"""Regression tests for v6 mislocalized test-only SWE-bench patches.

These use small synthetic repositories, never gold benchmark patches.
They do not establish an independent SWE-bench solve-rate improvement.
"""
import json
import tempfile
import unittest
from pathlib import Path

from repopilot.agentic_benchmark import propose_agentic_benchmark
from repopilot.context_select import (
    is_test_path, is_test_infrastructure_issue, ranked_source_context
)


class ImplementationLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        implementation = self.root / "xarray" / "core" / "variable.py"
        implementation.parent.mkdir(parents=True)
        implementation.write_text(
            "class Variable:\n"
            "    def indexing(self, indexes):\n"
            "        return indexes[:1]\n", encoding="utf-8")
        reproduction = self.root / "xarray" / "tests" / "test_variable.py"
        reproduction.parent.mkdir(parents=True)
        reproduction.write_text(
            "from xarray.core.variable import Variable\n"
            "class TestVariableIndexing:\n"
            "    def test_variable_indexing_wrong_length(self):\n"
            "        result = Variable().indexing([0, 1, 2])\n"
            "        assert result == [0, 1]\n", encoding="utf-8")

    def response(self, action):
        return {"choices": [{"message": {"content": json.dumps(action)}}]}

    def test_recognizes_nested_test_files_without_misclassifying_library(self):
        for path in ("tests/runtests.py", "xarray/tests/test_variable.py",
                     "pkg/test_foo.py", "pkg/foo_test.py", "conftest.py"):
            with self.subTest(path=path):
                self.assertTrue(is_test_path(path))
        for path in ("xarray/core/variable.py", "pkg/contest.py",
                     "src/_pytest/main.py"):
            with self.subTest(path=path):
                self.assertFalse(is_test_path(path))

    def test_test_traceback_is_not_explicit_test_infrastructure_request(self):
        self.assertFalse(is_test_infrastructure_issue(
            "Traceback from xarray/tests/test_variable.py shows wrong variable indexing"))
        self.assertTrue(is_test_infrastructure_issue(
            "Fix test runner discovery in tests/runtests.py"))

    def test_implementation_with_symbol_match_precedes_high_scoring_test(self):
        issue = ("Variable indexing wrong_length when x dimension selected, "
                 "shown by xarray/tests/test_variable.py assertion")
        results = ranked_source_context(self.root, issue, max_files=3)
        self.assertEqual(results[0].path, "xarray/core/variable.py")
        self.assertIn("xarray/tests/test_variable.py", [p.path for p in results])

    def test_explicit_test_traceback_preinspects_implementation_instead(self):
        seen = []
        action = {"action": "finish", "edits": [{
            "path": "xarray/core/variable.py",
            "old": "return indexes[:1]",
            "new": "return indexes[:2]",
        }]}
        def client(url, model, token, history):
            seen.append(list(history))
            return self.response(action)
        patch_spec, meta = propose_agentic_benchmark(
            self.root,
            "Bug in xarray/tests/test_variable.py: Variable.indexing drops a selected value",
            "mock", "http://127.0.0.1:11434/v1", client=client,
            max_steps=2, auto_issue_paths=True)
        self.assertIn("indexes[:2]", patch_spec.patch)
        self.assertIn("xarray/core/variable.py", meta["inspected_files"])
        self.assertNotIn("xarray/tests/test_variable.py", meta["inspected_files"])
        self.assertIn("ranked_initial_preinspect",
                      [event["action"] for event in meta["tool_trace"]])

    def test_test_only_candidate_rejected_when_impl_was_inspected(self):
        first = {"action": "finish", "edits": [{
            "path": "xarray/tests/test_variable.py",
            "old": "assert result == [0, 1]",
            "new": "assert result == [0]",
        }]}
        second = {"action": "finish", "edits": [{
            "path": "xarray/core/variable.py",
            "old": "return indexes[:1]",
            "new": "return indexes[:2]",
        }]}
        actions = iter((first, second))
        def client(url, model, token, history):
            return self.response(next(actions))
        patch_spec, meta = propose_agentic_benchmark(
            self.root, "Variable.indexing incorrect number of selected values",
            "mock", "http://127.0.0.1:11434/v1", client=client,
            max_steps=3, auto_issue_paths=True)
        self.assertIn("xarray/core/variable.py", patch_spec.patch)
        self.assertNotIn("diff --git a/xarray/tests", patch_spec.patch)
        self.assertIn("test_only_patch_rejected",
                      [event["action"] for event in meta["tool_trace"]])

    def test_explicit_test_runner_change_remains_legal(self):
        runner = self.root / "tests" / "runtests.py"
        runner.parent.mkdir()
        runner.write_text("def discovery():\n    return 'old'\n", encoding="utf-8")
        action = {"action": "finish", "edits": [{
            "path": "tests/runtests.py",
            "old": "return 'old'",
            "new": "return 'new'",
        }]}
        patch_spec, meta = propose_agentic_benchmark(
            self.root, "Fix test runner discovery in tests/runtests.py",
            "mock", "http://127.0.0.1:11434/v1",
            client=lambda *args: self.response(action),
            max_steps=2, auto_issue_paths=True)
        self.assertIn("return 'new'", patch_spec.patch)
        self.assertIn("tests/runtests.py", meta["inspected_files"])


if __name__ == "__main__":
    unittest.main()
