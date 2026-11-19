import tempfile
import unittest
from pathlib import Path
from repopilot.checkout_scope import resolve_repo_subdir

class ScopeTests(unittest.TestCase):
    def test_valid_nested_dir(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/"repopilot"/"examples").mkdir(parents=True)
            self.assertEqual(resolve_repo_subdir(root,"repopilot/examples"),root/"repopilot"/"examples")
    def test_refuse_parent(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                resolve_repo_subdir(Path(td),"../secrets")
    def test_refuse_absolute(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                resolve_repo_subdir(Path(td),"/etc")
    def test_refuse_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"external").symlink_to(Path(td).parent)
            with self.assertRaises(ValueError):
                resolve_repo_subdir(root,"external")
if __name__=="__main__":
    unittest.main()
