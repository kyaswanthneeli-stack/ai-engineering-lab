import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from repopilot.context_select import ranked_source_context,describe_context,_bounded_python_walk

class ContextSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/"unrelated.py").write_text("def plant_tree():\n    return 1\n")
        (self.root/"billing.py").write_text("def calculate_invoice_tax(price):\n    return price*0.2\n")
        (self.root/"orders.py").write_text("def create_order():\n    return 1\n")
    def test_issue_ranks_relevant_symbol_first(self):
        items=ranked_source_context(self.root,"calculate_invoice_tax is wrong")
        self.assertEqual(items[0].path,"billing.py")
        self.assertIn("calculate_invoice_tax",items[0].symbols)
        self.assertIn("FILE billing.py",describe_context(items))
    def test_explicit_mentioned_file_is_ranked_even_after_scan_limit(self):
        # Issue files must be considered even when outside the capped scan.
        (self.root/"zz_target.py").write_text("def target():\n    return 5\n")
        items=ranked_source_context(
            self.root,"Fix `zz_target.py` with the incorrect target logic.",
            max_files=1,scan_limit=1)
        self.assertEqual(items[0].path,"zz_target.py")

    def test_basename_mentioned_in_issue_locates_nested_source(self):
        nested=self.root/"package"/"deep"
        nested.mkdir(parents=True)
        (nested/"target_module.py").write_text(
            "def repair_target_module():\n    return 3\n")
        items=ranked_source_context(
            self.root,"Bug in target_module.py when calling repair_target_module",
            max_files=1,scan_limit=1)
        self.assertEqual(items[0].path,"package/deep/target_module.py")

    def test_limits(self):
        items=ranked_source_context(self.root,"tax",max_files=1,max_chars=900)
        self.assertEqual(len(items),1)
        self.assertLessEqual(len(items[0].text),900)
    def test_skips_symlinks(self):
        target=self.root.parent/"repoPilot-context-outside.py"
        target.write_text("def secret_outside():return 1\n")
        try:
            (self.root/"leak.py").symlink_to(target)
            self.assertNotIn("leak.py",[x.path for x in ranked_source_context(self.root,"secret_outside")])
        finally:
            target.unlink(missing_ok=True)
    def test_context_excludes_venv(self):
        venv=self.root/".venv";venv.mkdir()
        (venv/"bill.py").write_text("def calculate_invoice_tax():return 1\n")
        self.assertNotIn(".venv/bill.py",[x.path for x in ranked_source_context(self.root,"tax")])
    def test_rejects_unbounded_requested_context(self):
        with self.assertRaises(ValueError):
            ranked_source_context(self.root,"tax",max_chars=1000000)

    def test_source_index_avoids_unbounded_recursive_glob(self):
        # Old Path.rglob enumerated the whole repository before the limit.
        with patch.object(Path, "rglob", side_effect=AssertionError("unbounded glob")):
            items = ranked_source_context(self.root, "invoice tax error",
                                          scan_limit=1, max_files=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].path, "billing.py")

    def test_explicit_issue_path_bypasses_partial_large_repo_index(self):
        package = self.root / "deep" / "package"
        package.mkdir(parents=True)
        (package / "critical.py").write_text(
            "def fix_critical():\n    return True\n")
        for n in range(45):
            (self.root / f"a_noise_{n:02}.py").write_text(
                "def unrelated_name(): return False\n")
        items = ranked_source_context(
            self.root, "Fix deep/package/critical.py in the traceback",
            scan_limit=1, max_files=1)
        self.assertEqual(items[0].path, "deep/package/critical.py")

    def test_entry_budget_limits_directory_enumeration(self):
        root = self.root / "huge"
        (root / "a").mkdir(parents=True)
        (root / "b").mkdir()
        (root / "a" / "first.py").write_text("def first(): return 1\n")
        (root / "b" / "second.py").write_text("def second(): return 2\n")
        # Exactly the two top-level entries fit; nested files are not read.
        self.assertEqual(list(_bounded_python_walk(root, entry_limit=2)), [])
        self.assertEqual(
            {rel for _, rel in _bounded_python_walk(root, entry_limit=10)},
            {"a/first.py", "b/second.py"})

    def test_scan_limit_must_be_bounded(self):
        for value in (0, 20001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ranked_source_context(self.root, "tax", scan_limit=value)


    def test_truncation_marker_does_not_exceed_total_budget(self):
        (self.root / "large.py").write_text(
            "def calculate_invoice_tax(price):\n    return price * 0.2\n" +
            "# source body\n" * 800)
        for budget in (300, 500, 9000):
            with self.subTest(budget=budget):
                selected = ranked_source_context(
                    self.root, "Bug in large.py calculate_invoice_tax", max_files=1,
                    max_chars=budget)
                self.assertEqual(len(selected), 1)
                self.assertLessEqual(len(selected[0].text), budget)
                self.assertIn("context truncated", selected[0].text)

    def test_untrusted_explicit_issue_path_cannot_enter_excluded_directories(self):
        for name in (".venv", ".git", "node_modules", ".runs", "build"):
            directory = self.root / name
            directory.mkdir(exist_ok=True)
            (directory / "private.py").write_text("def dangerous_secret(): return 1\n")
        items = ranked_source_context(
            self.root,
            "Please fix .venv/private.py .git/private.py "
            "node_modules/private.py .runs/private.py build/private.py",
            max_files=20)
        self.assertFalse(any("private.py" in item.path for item in items))

if __name__=="__main__":
    unittest.main()
