import tempfile
import unittest
from pathlib import Path
from repopilot.graph import import_graph,module_name

class GraphTests(unittest.TestCase):
    def test_static_imports(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            pkg=root/"orders";pkg.mkdir()
            (pkg/"__init__.py").write_text("")
            (pkg/"price.py").write_text("def cost():return 3\n")
            (pkg/"service.py").write_text("from orders.price import cost\nimport json\n")
            g=import_graph(root)
            self.assertIn({"from":"orders.service","to":"orders.price"},g["imports"])
            self.assertFalse(any(e["to"]=="json" for e in g["imports"]))
    def test_relative_import(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);pkg=root/"app";pkg.mkdir()
            (pkg/"__init__.py").write_text("")
            (pkg/"data.py").write_text("x=1\n")
            (pkg/"work.py").write_text("from .data import x\n")
            g=import_graph(root)
            self.assertIn({"from":"app.work","to":"app.data"},g["imports"])
    def test_module_names(self):
        self.assertEqual(module_name("a/b/__init__.py"),"a.b")
        self.assertEqual(module_name("a/b.py"),"a.b")
    def test_parse_error_is_ignored(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/"broken.py").write_text("def :\n")
            self.assertEqual(import_graph(p)["modules"],[])
if __name__=="__main__":
    unittest.main()
