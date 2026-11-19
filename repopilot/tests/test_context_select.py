import tempfile
import unittest
from pathlib import Path
from repopilot.context_select import ranked_source_context,describe_context,issue_window_start

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


    def test_v2_deep_ast_function_selected_beyond_first_120_lines(self):
        module=self.root/"package"/"long_module.py"
        module.parent.mkdir()
        module.write_text(
            "".join(f"FILLER_{i} = {i}\\n" for i in range(260))
            + "def calculate_invoice_tax(price):\\n    return price*0.2\\n")
        start=issue_window_start(
            self.root,"package/long_module.py",
            "Bug in calculate_invoice_tax: incorrect invoice tax")
        self.assertGreater(start,200)
        lines=module.read_text().splitlines()
        self.assertIn("def calculate_invoice_tax", "\\n".join(lines[start-1:start+119]))

    def test_v2_traceback_position_prioritized_over_first_lines(self):
        module=self.root/"pkg"/"deep.py"
        module.parent.mkdir()
        module.write_text("".join(f"DATA_{i} = {i}\\n" for i in range(360)))
        start=issue_window_start(
            self.root,"pkg/deep.py",
            'Traceback: File "/tmp/source/pkg/deep.py", line 301, in run')
        self.assertEqual(start,289)

    def test_v2_unrelated_traceback_cannot_redirect_selected_file(self):
        (self.root/"long.py").write_text("".join(
            f"DATA_{i} = {i}\\n" for i in range(260)))
        self.assertEqual(issue_window_start(
            self.root,"long.py",
            'Error File "/somewhere/unrelated.py", line 200'),1)

    def test_v2_window_rejects_traversal_and_symlinks(self):
        with self.assertRaises(ValueError):
            issue_window_start(self.root,"../secret.py","secret")
        with self.assertRaises(ValueError):
            issue_window_start(self.root,"billing.py","tax",count=10000)
        target=self.root.parent/"context-window-outside.py"
        target.write_text("def leak(): pass\\n")
        try:
            (self.root/"outside.py").symlink_to(target)
            with self.assertRaises(ValueError):
                issue_window_start(self.root,"outside.py","leak")
        finally:
            target.unlink(missing_ok=True)

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
if __name__=="__main__":
    unittest.main()
