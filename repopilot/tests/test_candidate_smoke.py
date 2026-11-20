"""Candidate smoke must be isolated, bounded and conservative.

These are controlled fixtures, never official SWE-bench solve claims.
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, call

from repopilot.candidate_smoke import (
    _reproducer, _run_docker, smoke_candidate
)
from repopilot.agentic_benchmark import propose_agentic_benchmark, AgentToolError


DIFF = ("diff --git a/pricing.py b/pricing.py\n"
        "--- a/pricing.py\n+++ b/pricing.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def price(x):\n"
        "-    return x + 1\n"
        "+    return x - 1\n")


class CandidateSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/"pricing.py").write_text(
            "def price(x):\n    return x + 1\n", encoding="utf-8")
        self.issue = ("Unexpected result when applying price()\n"
                      "```python\nfrom pricing import price\n"
                      "assert price(5) >= 0\n```")

    def test_parse_python_issue_reproducer_without_host_execution(self):
        script, kind = _reproducer(self.issue, ["pricing.py"])
        self.assertEqual(kind, "issue_python_example")
        self.assertIn("assert price(5)", script)

    def test_invalid_issue_code_falls_back_to_import(self):
        script, kind = _reproducer(
            "```python\nif broken::\n```", ["pricing.py"])
        self.assertEqual(kind, "module_import")
        self.assertIn("importlib.import_module('pricing')", script)

    def test_rejects_new_failure_after_passing_baseline(self):
        with patch("repopilot.candidate_smoke.shutil.which",
                   return_value="/usr/bin/docker"), patch(
                   "repopilot.candidate_smoke._run_docker",
                   side_effect=[(0, False), (1, False)]) as runner:
            report = smoke_candidate(self.root, DIFF, self.issue)
        self.assertEqual(report["status"], "regression")
        self.assertEqual(report["reason"], "baseline_passed_candidate_failed")
        self.assertEqual(runner.call_count, 2)
        self.assertIsNone(runner.call_args_list[0].kwargs["overlay"])
        self.assertIsNotNone(runner.call_args_list[1].kwargs["overlay"])
        self.assertEqual(
            (self.root/"pricing.py").read_text(),
            "def price(x):\n    return x + 1\n")

    def test_baseline_failure_is_inconclusive_and_not_blocked(self):
        # An issue example that fails against the original may reproduce the
        # reported bug. The bounded import fallback also fails here, so no
        # regression or successful verification can be claimed.
        with patch("repopilot.candidate_smoke.shutil.which",
                   return_value="/usr/bin/docker"), patch(
                   "repopilot.candidate_smoke._run_docker",
                   side_effect=[(1, False), (1, False)]) as runner:
            report = smoke_candidate(self.root, DIFF, self.issue)
        self.assertEqual(report["status"], "inconclusive")
        self.assertEqual(report["reason"], "baseline_did_not_pass")
        self.assertEqual(runner.call_count, 2)

    def test_both_pass_only_limited_smoke_not_official_solve(self):
        with patch("repopilot.candidate_smoke.shutil.which",
                   return_value="/usr/bin/docker"), patch(
                   "repopilot.candidate_smoke._run_docker",
                   side_effect=[(0, False), (0, False)]):
            report = smoke_candidate(self.root, DIFF, self.issue)
        self.assertEqual(report["status"], "no_regression_observed")
        self.assertEqual(report["reason"], "limited_probe_only")

    def test_missing_docker_is_never_marked_passing(self):
        with patch("repopilot.candidate_smoke.shutil.which",
                   return_value=None):
            self.assertEqual(smoke_candidate(
                self.root, DIFF, self.issue)["status"], "skipped")

    def test_sandbox_command_cannot_access_network_or_host_write(self):
        class Completed:
            returncode = 0
        args_seen = []
        def fake_run(args, **kwargs):
            args_seen.append(args)
            return Completed()
        with patch("repopilot.candidate_smoke.subprocess.run",
                   side_effect=fake_run):
            code, unsafe = _run_docker(
                self.root, "import pricing", overlay=None,
                targets=["pricing.py"], timeout=6)
        self.assertEqual((code, unsafe), (0, False))
        args = args_seen[0]
        for flag in ("--network=none", "--cap-drop=ALL",
                     "--security-opt=no-new-privileges",
                     "--read-only", "--user=65534:65534",
                     "--memory=512m", "--cpus=1"):
            self.assertIn(flag, args)
        self.assertEqual(args[-3], "python")
        self.assertEqual(args[-2], "-c")
        self.assertFalse(any("token" in str(x).lower() for x in args))

    def test_cleanup_failure_marks_result_unsafe(self):
        def fake_run(args, **kwargs):
            if args[:2] == ["docker", "run"]:
                raise subprocess.TimeoutExpired(args, 1)
            return subprocess.CompletedProcess(args, 1)
        with patch("repopilot.candidate_smoke.subprocess.run",
                   side_effect=fake_run):
            exit_code, unsafe = _run_docker(
                self.root, "import pricing", overlay=None,
                targets=["pricing.py"], timeout=1)
        self.assertIsNone(exit_code)
        self.assertTrue(unsafe)

    def test_invalid_timeout_refused_before_docker(self):
        for value in (0, 7, 31, 60):
            with self.subTest(value=value), self.assertRaises(ValueError):
                smoke_candidate(self.root, DIFF, self.issue, timeout=value)

    def test_agent_rejects_regression_then_requests_new_patch(self):
        bad = {"action":"finish", "edits":[{
            "path":"pricing.py", "old":"return x + 1", "new":"return x - 1"}]}
        good = {"action":"finish", "edits":[{
            "path":"pricing.py", "old":"return x + 1", "new":"return x + 2"}]}
        actions = iter((bad, good))
        def client(*_):
            return {"choices":[{"message":{"content":json.dumps(next(actions))}}]}
        with patch.dict("os.environ",
                        {"REPOPILOT_CANDIDATE_SMOKE":"1"}), patch(
                        "repopilot.agentic_benchmark.smoke_candidate",
                        side_effect=[{"status":"regression"},
                                     {"status":"no_regression_observed"}]) as checker:
            result, meta = propose_agentic_benchmark(
                self.root, "fix pricing", "model",
                "http://127.0.0.1:11434/v1", client=client,
                max_steps=3, required_targets={"pricing.py"})
        self.assertIn("return x + 2", result.patch)
        self.assertNotIn("+    return x - 1", result.patch)
        self.assertEqual(checker.call_count, 2)
        self.assertEqual(meta["candidate_smoke"]["status"],
                         "no_regression_observed")
        self.assertEqual(
            [x["status"] for x in meta["tool_trace"]
             if x["action"] == "candidate_smoke"],
            ["regression", "no_regression_observed"])

    def test_agent_refuses_last_step_regressing_patch(self):
        bad = {"action":"finish", "edits":[{
            "path":"pricing.py", "old":"return x + 1", "new":"return x - 1"}]}
        def client(*_):
            return {"choices":[{"message":{"content":json.dumps(bad)}}]}
        with patch.dict("os.environ",
                        {"REPOPILOT_CANDIDATE_SMOKE":"1"}), patch(
                        "repopilot.agentic_benchmark.smoke_candidate",
                        return_value={"status":"regression"}):
            with self.assertRaisesRegex(
                    AgentToolError,"sandbox smoke regression"):
                propose_agentic_benchmark(
                    self.root, "fix pricing", "model",
                    "http://127.0.0.1:11434/v1", client=client,
                    max_steps=2, required_targets={"pricing.py"})


if __name__ == "__main__":
    unittest.main()
