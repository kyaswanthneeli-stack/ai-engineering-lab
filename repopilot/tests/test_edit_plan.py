import tempfile
import unittest
from pathlib import Path
from repopilot.edit_plan import canonical_patch, canonical_line_patch, EditPlanError
from repopilot.patches import apply_patch


class EditPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / "pricing.py").write_text("def subtotal(items):\n    return sum(items)\n")
        (self.repo / "checkout.py").write_text("from pricing import subtotal\ndef total(items):\n    return subtotal(items)\n")
        self.allowed = {"pricing.py", "checkout.py"}

    def test_inspected_line_edit_fixes_duplicate_text_by_line_number(self):
        source="def left():\n    return 0\n\ndef right():\n    return 0\n"
        (self.repo/"pricing.py").write_text(source)
        patch=canonical_line_patch(
            self.repo,[{"path":"pricing.py","start_line":5,"end_line":5,
                        "new":"    return 1"}],
            allowed_files={"pricing.py"},
            inspected_windows={"pricing.py":[(4,5)]})
        self.assertEqual((self.repo/"pricing.py").read_text(),source)
        apply_patch(self.repo,patch)
        self.assertEqual((self.repo/"pricing.py").read_text(),
                         "def left():\n    return 0\n\ndef right():\n    return 1\n")

    def test_inspected_line_edits_require_known_line_window(self):
        original=(self.repo/"pricing.py").read_text()
        def one(start,end,**overrides):
            e={"path":"pricing.py","start_line":start,
               "end_line":end,"new":"    return 2"}
            e.update(overrides)
            return e
        valid={"pricing.py":[(1,1)]}
        for edits in ([one(2,2)],[one(2,3)],[one(1,1,start_line=True)],
                      [one(1,2,end_line=999999)],[one(1,1,command="shell")]):
            with self.subTest(edits=edits),self.assertRaises(EditPlanError):
                canonical_line_patch(self.repo,edits,
                    allowed_files={"pricing.py"},inspected_windows=valid)
        self.assertEqual((self.repo/"pricing.py").read_text(),original)

    def test_inspected_line_edits_reject_overlapping_ranges(self):
        with self.assertRaisesRegex(EditPlanError,"Overlapping"):
            canonical_line_patch(self.repo,[
                {"path":"pricing.py","start_line":1,"end_line":2,"new":"def subtotal(items):\n    return 5\n"},
                {"path":"pricing.py","start_line":2,"end_line":2,"new":"    return 6"}],
                allowed_files={"pricing.py"},inspected_windows={"pricing.py":[(1,2)]})

    def test_inspected_line_edits_reject_uninspected_and_symlink_paths(self):
        for value in ("checkout.py","../outside.py","/etc/passwd","unknown.py"):
            with self.subTest(value=value),self.assertRaises(EditPlanError):
                canonical_line_patch(self.repo,[
                    {"path":value,"start_line":1,"end_line":1,
                     "new":"return 5"}],allowed_files={"pricing.py"},
                    inspected_windows={"pricing.py":[(1,2)]})
        outside=self.repo.parent/"repopilot-line-edit-secret.py"
        outside.write_text("SECRET=1\n")
        try:
            (self.repo/"linked.py").symlink_to(outside)
            with self.assertRaises(EditPlanError):
                canonical_line_patch(self.repo,[
                    {"path":"linked.py","start_line":1,"end_line":1,
                     "new":"SECRET=2"}],allowed_files={"linked.py"},
                    inspected_windows={"linked.py":[(1,1)]})
        finally:
            (self.repo/"linked.py").unlink()
            outside.unlink()

    def test_inspected_line_edits_reject_long_line_not_fully_read(self):
        (self.repo/"long.py").write_text("x = '"+("a"*350)+"'\n")
        with self.assertRaisesRegex(EditPlanError,"truncated source"):
            canonical_line_patch(self.repo,[
                {"path":"long.py","start_line":1,"end_line":1,
                 "new":"x = 'short'"}],allowed_files={"long.py"},
                inspected_windows={"long.py":[(1,1)]})

    def test_valid_multifile_patch_applies(self):
        edits = [
            {"path": "pricing.py", "old": "return sum(items)", "new": "return round(sum(items), 2)"},
            {"path": "checkout.py", "old": "return subtotal(items)", "new": "return round(subtotal(items), 2)"},
        ]
        patch = canonical_patch(self.repo, edits, allowed_files=self.allowed)
        self.assertEqual(patch.count("diff --git"), 2)
        apply_patch(self.repo, patch)
        self.assertIn("round(sum(items), 2)", (self.repo/"pricing.py").read_text())
        self.assertIn("round(subtotal(items), 2)", (self.repo/"checkout.py").read_text())

    def test_rejects_missing_or_ambiguous_old_text(self):
        with self.assertRaises(EditPlanError):
            canonical_patch(self.repo, [{"path": "pricing.py", "old": "does not exist", "new": "x"}], allowed_files=self.allowed)
        (self.repo/"pricing.py").write_text("x = 1\nx = 1\n")
        with self.assertRaises(EditPlanError):
            canonical_patch(self.repo, [{"path": "pricing.py", "old": "x = 1", "new": "x = 2"}], allowed_files=self.allowed)

    def test_rejects_traversal_and_unindexed_files(self):
        for path in ("../escape.py", "other.py", "/etc/passwd"):
            with self.subTest(path=path), self.assertRaises(EditPlanError):
                canonical_patch(self.repo, [{"path": path, "old": "a", "new": "b"}], allowed_files=self.allowed)

    def test_rejects_symlinks(self):
        outside = self.repo.parent / "repopilot-edit-plan-external.py"
        outside.write_text("some_secret = 1\n")
        try:
            (self.repo/"leak.py").symlink_to(outside)
            with self.assertRaises(EditPlanError):
                canonical_patch(self.repo, [{"path": "leak.py", "old": "some_secret", "new": "x"}], allowed_files=self.allowed|{"leak.py"})
        finally:
            outside.unlink(missing_ok=True)

    def test_rejects_unrecognized_commands(self):
        with self.assertRaises(EditPlanError):
            canonical_patch(self.repo, [{"path":"pricing.py","old":"return sum(items)","new":"return 1","command":"rm -rf"}],allowed_files=self.allowed)

    def test_no_partial_repository_mutation_on_error(self):
        original = (self.repo/"pricing.py").read_text()
        edits = [
            {"path": "pricing.py", "old":"return sum(items)", "new":"return 0"},
            {"path": "checkout.py", "old":"not here", "new":"x"}
        ]
        with self.assertRaises(EditPlanError):
            canonical_patch(self.repo, edits, allowed_files=self.allowed)
        self.assertEqual((self.repo/"pricing.py").read_text(), original)

    def test_multiple_replacements_same_file(self):
        edits = [
            {"path":"pricing.py","old":"def subtotal(items)","new":"def subtotal(prices)"},
            {"path":"pricing.py","old":"return sum(items)","new":"return sum(prices)"},
        ]
        patch = canonical_patch(self.repo, edits, allowed_files=self.allowed)
        apply_patch(self.repo, patch)
        self.assertEqual((self.repo/"pricing.py").read_text(), "def subtotal(prices):\n    return sum(prices)\n")


if __name__ == "__main__":
    unittest.main()
