import tempfile
import unittest
from pathlib import Path
from repopilot.edit_plan import canonical_patch, EditPlanError
from repopilot.patches import apply_patch


class EditPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / "pricing.py").write_text("def subtotal(items):\n    return sum(items)\n")
        (self.repo / "checkout.py").write_text("from pricing import subtotal\ndef total(items):\n    return subtotal(items)\n")
        self.allowed = {"pricing.py", "checkout.py"}

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
