import subprocess
import tempfile
import unittest
from pathlib import Path
from repopilot.patch_repair import reconstruct_single_hunk,PatchRepairError

SOURCE="def divide(a, b):\n    if b == 0:\n        return 0  # BUG: should raise ZeroDivisionError\n    return a / b\n"
BAD="diff --git a/calculator.py b/calculator.py\n--- a/calculator.py\n+++ b/calculator.py\n@@ -1,5 +1,5 @@\n def divide(a, b):\n-    if b == 0:\n-        return 0  # BUG: should raise ZeroDivisionError\n+    if b == 0:\n+        raise ZeroDivisionError('Division by zero')\n     return a / b\n"

class PatchNormalizationTests(unittest.TestCase):
    def test_normalize_model_change_with_wrong_hunk_count(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"calculator.py").write_text(SOURCE)
            patch=reconstruct_single_hunk(root,BAD)
            self.assertIn("@@ -1,4 +1,4 @@",patch)
            self.assertIn("raise ZeroDivisionError('Division by zero')",patch)
            check=subprocess.run(["git","apply","--check","-"],input=patch,cwd=root,capture_output=True,text=True)
            self.assertEqual(check.returncode,0,check.stderr)
            self.assertEqual((root/"calculator.py").read_text(),SOURCE) # normalization does not mutate source
    def test_reject_nonunique_removed_block(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"calculator.py").write_text(SOURCE+SOURCE)
            with self.assertRaises(PatchRepairError):
                reconstruct_single_hunk(root,BAD)
    def test_reject_wrong_deleted_lines(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"calculator.py").write_text(SOURCE.replace("return 0  # BUG: should raise ZeroDivisionError","return 999"))
            with self.assertRaises(PatchRepairError):
                reconstruct_single_hunk(root,BAD)
    def test_reject_forged_context_even_when_deleted_text_exists(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"calculator.py").write_text(SOURCE)
            forged=BAD.replace(" def divide(a, b):", " def other_function(a, b):")
            with self.assertRaises(PatchRepairError):
                reconstruct_single_hunk(root,forged)

    def test_preserve_context_between_separated_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source="first = 1\nintermediate = 2\nlast = 3\n"
            root.joinpath("calculator.py").write_text(source)
            malformed=("diff --git a/calculator.py b/calculator.py\n"
                       "--- a/calculator.py\n+++ b/calculator.py\n"
                       "@@ -1,4 +1,4 @@\n-first = 1\n"
                       " intermediate = 2\n-last = 3\n"
                       "+first = 10\n+last = 30\n")
            patch=reconstruct_single_hunk(root,malformed)
            self.assertIn("intermediate = 2",patch)
            self.assertEqual(root.joinpath("calculator.py").read_text(),source)

if __name__=="__main__":unittest.main()
