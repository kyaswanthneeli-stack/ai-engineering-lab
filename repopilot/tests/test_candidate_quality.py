"""Actual private-overlay checks and bounded agent recovery for quote-only edits."""
import difflib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from repopilot.agentic_benchmark import propose_agentic_benchmark, AgentToolError
from repopilot.candidate_quality import review_quote_only_patch


def diff(name, before, after):
    return f"diff --git a/{name} b/{name}\n" + "".join(
        difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                             fromfile="a/" + name, tofile="b/" + name))


class CandidateQualityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        # Reproduce the actual unscored pytest proposal without importing code.
        self.before = 'hookimpl = HookimplMarker("pytest")\n'
        self.quote = "hookimpl = HookimplMarker('pytest')\n"
        (self.root / "hooks.py").write_text(self.before)

    def test_real_quote_only_pattern_rejected_without_modifying_original(self):
        result = review_quote_only_patch(
            self.root, diff("hooks.py", self.before, self.quote))
        self.assertEqual(result["status"], "quote_only")
        self.assertEqual((self.root / "hooks.py").read_text(), self.before)

    def test_value_fstring_comment_directive_and_line_changes_not_rejected(self):
        cases = [
            (self.before, 'hookimpl = HookimplMarker("other!")\n'),
            ('value = f"{one}"\n', 'value = f"{two}"\n'),
            ('value = "x"  # type: str\n', 'value = "x"  # type: int\n'),
            ('value = "x"\n', '\nvalue = "x"\n'),
            ('value = "x"\n', 'value = "x"  # noqa\n'),
            ('value = b"x"\n', 'value = "x"\n'),
        ]
        for before, after in cases:
            with self.subTest(after=after):
                (self.root / "hooks.py").write_text(before)
                result = review_quote_only_patch(
                    self.root, diff("hooks.py", before, after))
                self.assertEqual(result["status"], "changed_or_unknown")

    def test_mixed_multifile_patch_with_value_change_is_not_quote_only(self):
        (self.root / "value.py").write_text("value = 1\n")
        proposal = diff("hooks.py", self.before, self.quote)
        proposal += diff("value.py", "value = 1\n", "value = 2\n")
        self.assertEqual(review_quote_only_patch(
            self.root, proposal)["status"], "changed_or_unknown")

    def test_invalid_candidate_syntax_distinguished_from_unavailable_analysis(self):
        self.assertEqual(review_quote_only_patch(
            self.root, diff("hooks.py", self.before, "value = (\n"))["status"],
            "invalid_python")
        self.assertEqual(review_quote_only_patch(
            self.root, diff("hooks.py", "missing = 1\n", "missing = 2\n"))["status"],
            "unavailable")
        self.assertEqual((self.root / "hooks.py").read_text(), self.before)

    def test_compile_regression_in_second_file_not_hidden_by_first_valid_change(self):
        (self.root / "other.py").write_text("def f():\n    return 1\n")
        proposal = diff("hooks.py", self.before, "value = 3\n")
        proposal += diff("other.py", "def f():\n    return 1\n",
                         "def f():\nreturn 2\n")
        self.assertEqual(review_quote_only_patch(
            self.root, proposal)["status"], "invalid_python")
        self.assertEqual((self.root / "other.py").read_text(), "def f():\n    return 1\n")

    def test_original_unsupported_syntax_is_not_candidate_regression(self):
        original = "print 1\n"
        (self.root / "hooks.py").write_text(original)
        self.assertEqual(review_quote_only_patch(
            self.root, diff("hooks.py", original, "print 2\n"))["status"], "unavailable")

    def test_rejects_invalid_compilation_even_when_quote_gate_disabled(self):
        def client(*args):
            return {"choices":[{"message":{"content":json.dumps({
                "action":"finish","edits":[{"path":"hooks.py",
                "old":self.before,"new":"return 2\n"}]})}}]}
        with patch.dict("os.environ", {"REPOPILOT_REJECT_QUOTE_ONLY":"0",
                                      "REPOPILOT_CANDIDATE_SMOKE":"1"}), patch(
                "repopilot.agentic_benchmark.smoke_candidate") as smoke:
            with self.assertRaisesRegex(AgentToolError,"Python compile regression"):
                propose_agentic_benchmark(self.root,"Fix hook behavior","mock",
                    "http://127.0.0.1:11434/v1",client=client,
                    required_targets={"hooks.py"},max_steps=2)
        smoke.assert_not_called()
        self.assertEqual((self.root / "hooks.py").read_text(), self.before)

    def test_symlinked_parent_and_oversized_source_unavailable(self):
        with tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "hooks.py").write_text(self.before)
            (self.root / "linked").symlink_to(outside, target_is_directory=True)
            self.assertEqual(review_quote_only_patch(self.root,
                diff("linked/hooks.py", self.before, self.quote))["status"],
                "unavailable")
        (self.root / "hooks.py").write_text("#" * 100_001)
        self.assertEqual(review_quote_only_patch(self.root,
            diff("hooks.py", self.before, self.quote))["status"], "unavailable")

    def test_static_analysis_never_imports_target_source(self):
        sentinel = self.root / "executed"
        before = f'open({str(sentinel)!r}, "w").write("unsafe")\n' + self.before
        after = before.replace('HookimplMarker("pytest")', "HookimplMarker('pytest')")
        (self.root / "hooks.py").write_text(before)
        self.assertEqual(review_quote_only_patch(self.root,
            diff("hooks.py", before, after))["status"], "quote_only")
        self.assertFalse(sentinel.exists())

    def test_agent_corrects_all_three_finish_schemas_within_same_budget(self):
        for schema in ("edits", "files", "patch"):
            with self.subTest(schema=schema):
                if schema == "edits":
                    first = {"action": "finish", "edits": [{"path": "hooks.py",
                        "old": self.before, "new": self.quote}]}
                elif schema == "files":
                    first = {"action": "finish", "files": [{"path": "hooks.py",
                        "content": self.quote}]}
                else:
                    first = {"action": "finish", "patch": diff(
                        "hooks.py", self.before, self.quote)}
                second = {"action": "finish", "edits": [{"path": "hooks.py",
                    "old": '"pytest"', "new": '"pytest2"'}]}
                calls = []
                actions = iter([first, second])
                def client(*args):
                    calls.append(list(args[-1]))
                    return {"choices": [{"message": {
                        "content": json.dumps(next(actions))}}]}
                with patch.dict("os.environ", {"REPOPILOT_REJECT_QUOTE_ONLY": "1"}):
                    candidate, meta = propose_agentic_benchmark(self.root,
                        "Fix the hook namespace", "mock",
                        "http://127.0.0.1:11434/v1", client=client,
                        required_targets={"hooks.py"}, max_steps=2)
                self.assertEqual(len(calls), 2)
                self.assertIn('HookimplMarker("pytest2")', candidate.patch)
                self.assertTrue(any(x.get("error_type") == "QuoteOnlyProposal"
                                    for x in meta["tool_trace"]))
                self.assertTrue(any("quote-only" in m["content"] for m in calls[1]))
                self.assertEqual((self.root / "hooks.py").read_text(), self.before)

    def test_repeated_quote_only_attempts_fail_without_smoke_or_extra_model_calls(self):
        calls = []
        def client(*args):
            calls.append(1)
            return {"choices": [{"message": {"content": json.dumps({
                "action": "finish", "patch": diff(
                    "hooks.py", self.before, self.quote)})}}]}
        with patch.dict("os.environ", {"REPOPILOT_REJECT_QUOTE_ONLY": "1",
                                      "REPOPILOT_CANDIDATE_SMOKE": "1"}), patch(
                "repopilot.agentic_benchmark.smoke_candidate") as smoke:
            with self.assertRaisesRegex(AgentToolError, "Quote-only proposal"):
                propose_agentic_benchmark(self.root, "Fix hook namespace", "mock",
                    "http://127.0.0.1:11434/v1", client=client,
                    required_targets={"hooks.py"}, max_steps=2)
        self.assertEqual(len(calls), 2)
        smoke.assert_not_called()

    def test_operator_can_disable_heuristic_for_source_reflection_issues(self):
        def client(*args):
            return {"choices": [{"message": {"content": json.dumps({
                "action": "finish", "patch": diff(
                    "hooks.py", self.before, self.quote)})}}]}
        with patch.dict("os.environ", {"REPOPILOT_REJECT_QUOTE_ONLY": "0"}):
            _, meta = propose_agentic_benchmark(self.root, "Fix source representation",
                "mock", "http://127.0.0.1:11434/v1", client=client,
                required_targets={"hooks.py"}, max_steps=2)
        self.assertEqual(meta["candidate_quality"]["status"], "quote_only")
        self.assertFalse(meta["officially_evaluated"])
