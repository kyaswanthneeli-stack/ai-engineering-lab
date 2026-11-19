import tempfile
import unittest
import contextlib
import io
import json
from pathlib import Path
from repopilot.graph import import_graph,module_name,dependent_modules

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
    def test_transitive_impact_and_cycle_safety(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            (root/"base.py").write_text("import middle\\n".replace("\\n","\n"))
            (root/"middle.py").write_text("import base\\n".replace("\\n","\n"))
            (root/"api.py").write_text("import middle\\n".replace("\\n","\n"))
            (root/"unused.py").write_text("x=1\\n".replace("\\n","\n"))
            graph=import_graph(root)
            result=dependent_modules(graph,["base"])
            self.assertEqual(result["dependents"],
                [{"module":"middle","distance":1},{"module":"api","distance":2}])
            self.assertEqual(dependent_modules(graph,["base"],max_depth=1)["dependents"],
                [{"module":"middle","distance":1}])
            with self.assertRaises(ValueError):
                dependent_modules(graph,["missing"])

    def test_cli_impact_output(self):
        from repopilot.cli import main
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            (root/"storage.py").write_text("x=1\\n".replace("\\n","\n"))
            (root/"service.py").write_text("import storage\\n".replace("\\n","\n"))
            result=io.StringIO()
            with contextlib.redirect_stdout(result):
                main(["graph",str(root),"--impact","storage"])
            self.assertEqual(json.loads(result.getvalue())["dependents"],
                             [{"module":"service","distance":1}])

    def test_module_names(self):
        self.assertEqual(module_name("a/b/__init__.py"),"a.b")
        self.assertEqual(module_name("a/b.py"),"a.b")
    def test_parse_error_is_ignored(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/"broken.py").write_text("def :\n")
            self.assertEqual(import_graph(p)["modules"],[])
if __name__=="__main__":
    unittest.main()
