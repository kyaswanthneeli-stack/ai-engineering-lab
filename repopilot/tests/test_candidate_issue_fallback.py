"""Regression tests for issue examples that deliberately fail on original code.

A public issue snippet may reproduce an existing bug. Its baseline failure is
not a newly introduced regression. An optional module import can serve as a
weaker fallback if it actually passes on the pristine original.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repopilot.candidate_smoke import smoke_candidate

DIFF = (
    "diff --git a/pricing.py b/pricing.py\n"
    "--- a/pricing.py\n+++ b/pricing.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def price(x):\n"
    "-    return x + 1\n"
    "+    return x - 1\n"
)
ISSUE = (
    "Bug reproduction (expected to fail before fix)\n"
    "```python\nfrom pricing import price\n"
    "assert price(1) == 99\n```"
)


class CandidateIssueBaselineFallbackTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "pricing.py").write_text(
            "def price(x):\n    return x + 1\n", encoding="utf-8")

    def run_smoke_with(self, outcomes, *, issue=ISSUE, timeout=18):
        with patch("repopilot.candidate_smoke.shutil.which",
                   return_value="/usr/bin/docker"), patch(
                   "repopilot.candidate_smoke._run_docker",
                   side_effect=outcomes) as run:
            result = smoke_candidate(
                self.root, DIFF, issue, timeout=timeout)
        return result, run

    def test_regression_is_detected_only_after_fallback_baseline_passes(self):
        result, run = self.run_smoke_with(
            [(1, False), (0, False), (1, False)])
        self.assertEqual(result["status"], "regression")
        self.assertEqual(result["probe"], "module_import_fallback")
        self.assertEqual(result["reason"], "baseline_passed_candidate_failed")
        self.assertEqual(run.call_count, 3)
        self.assertIn("assert price(1) == 99", run.call_args_list[0].args[1])
        self.assertIn("importlib.import_module('pricing')",
                      run.call_args_list[1].args[1])
        self.assertEqual(run.call_args_list[1].args[1],
                         run.call_args_list[2].args[1])
        self.assertIsNone(run.call_args_list[1].kwargs["overlay"])
        self.assertIsNotNone(run.call_args_list[2].kwargs["overlay"])
        self.assertEqual(
            (self.root / "pricing.py").read_text(encoding="utf-8"),
            "def price(x):\n    return x + 1\n")

    def test_import_fallback_pass_on_both_sides_is_not_official_solve(self):
        result, run = self.run_smoke_with(
            [(1, False), (0, False), (0, False)])
        self.assertEqual(result["status"], "no_regression_observed")
        self.assertEqual(result["probe"], "module_import_fallback")
        self.assertEqual(result["reason"], "limited_probe_only")
        self.assertEqual(run.call_count, 3)

    def test_failing_fallback_remains_inconclusive(self):
        result, run = self.run_smoke_with(
            [(1, False), (1, False)])
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["reason"], "baseline_did_not_pass")
        self.assertEqual(result["probe"], "issue_python_example")
        self.assertEqual(run.call_count, 2)

    def test_no_issue_example_original_fail_has_no_fallback(self):
        result, run = self.run_smoke_with(
            [(1, False)], issue="Unexpected behavior from pricing")
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["probe"], "module_import")
        run.assert_called_once()

    def test_passing_issue_example_preserves_original_probe(self):
        result, run = self.run_smoke_with(
            [(0, False), (1, False)])
        self.assertEqual(result["status"], "regression")
        self.assertEqual(result["probe"], "issue_python_example")
        self.assertEqual(run.call_count, 2)

    def test_fallback_cleanup_failure_is_inconclusive_not_a_pass(self):
        result, run = self.run_smoke_with(
            [(1, False), (None, True)])
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["reason"], "container_cleanup_unconfirmed")
        self.assertEqual(run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
