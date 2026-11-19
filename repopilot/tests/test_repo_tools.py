import tempfile
import unittest
from pathlib import Path
from repopilot.repo_tools import read_python,list_python_files,search_python,InspectionError


class ToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)
        (self.repo/"billing.py").write_text("def add_tax(value):\n    return value * 1.1\n")
        (self.repo/"checkout.py").write_text("from billing import add_tax\n")

    def test_list_python_files(self):
        self.assertEqual(list_python_files(self.repo)["files"],["billing.py","checkout.py"])
    def test_search_literal(self):
        data=search_python(self.repo,"add_tax")
        self.assertEqual(len(data["matches"]),2)
        self.assertIn("path",data["matches"][0])
    def test_read_bounded(self):
        data=read_python(self.repo,"billing.py",start=2,count=1)
        self.assertEqual(data["lines"][0]["line"],2)
        self.assertIn("return",data["lines"][0]["text"])
    def test_reject_path_traversal(self):
        with self.assertRaises(InspectionError):
            read_python(self.repo,"../secret.py")
    def test_reject_non_python(self):
        with self.assertRaises(InspectionError):
            read_python(self.repo,".env")
    def test_symlink_blocked(self):
        (self.repo/"link.py").symlink_to(self.repo/"billing.py")
        with self.assertRaises(InspectionError):
            read_python(self.repo,"link.py")
    def test_no_arbitrary_regex(self):
        with self.assertRaises(InspectionError):
            search_python(self.repo,".")
if __name__=="__main__":
    unittest.main()
