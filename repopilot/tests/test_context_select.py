import tempfile
import unittest
from pathlib import Path
from repopilot.context_select import ranked_source_context,describe_context

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
        (self.root/"zz_target.py").write_text("def target():\\n    return 5\\n")
        items=ranked_source_context(
            self.root,"Fix `zz_target.py` with the incorrect target logic.",
            max_files=1,scan_limit=1)
        self.assertEqual(items[0].path,"zz_target.py")

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
