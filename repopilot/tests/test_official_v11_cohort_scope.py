"""Ensure the 7B v11 official cohort cannot quietly become an assisted case."""
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from repopilot.agentic_benchmark import _provider_timeout_seconds
from repopilot.benchmark_attempt import bounded_issue_context, configured_issue_context_chars
from repopilot.swebench_export import load_manifest


ROOT = Path(__file__).resolve().parents[1]
WF = ROOT.parent / ".github/workflows/repopilot-official-12-v11-7b-evaluation.yml"


class OfficialV11CohortScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WF.read_text(encoding="utf-8")

    def test_pinned_original_twelve_tasks_not_assisted_subset(self):
        manifest = load_manifest(ROOT / "benchmarks/swebench-lite-12.json")
        self.assertEqual(len(manifest), 12)
        self.assertEqual(len({t["instance_id"] for t in manifest}), 12)
        self.assertIn("python -m repopilot.benchmark_batch", self.workflow)
        self.assertIn("--manifest benchmarks/swebench-lite-12.json", self.workflow)
        self.assertIn("repopilot-official-12-v11-7b-evaluation.yml", self.workflow)
        self.assertNotIn("ci/django_sqlite/retry.py", self.workflow)
        self.assertNotIn("required_targets=", self.workflow)
        self.assertNotIn("exact_edit_anchors=", self.workflow)
        self.assertNotIn("--instance_ids django__django-12113", self.workflow)

    def test_uniform_model_budget_is_within_supported_bounds(self):
        settings = dict(re.findall(
            r"^\s+(REPOPILOT_[A-Z_]+):\s*'([^']+)'\s*$",
            self.workflow, re.MULTILINE))
        self.assertEqual(settings["REPOPILOT_MODEL"], "qwen2.5-coder:7b")
        self.assertEqual(settings["REPOPILOT_PROVIDER_TIMEOUT_SECONDS"], "120")
        with patch.dict("os.environ", settings):
            self.assertEqual(_provider_timeout_seconds(), 120)
            self.assertEqual(configured_issue_context_chars(), 6500)
        budget = int(settings["REPOPILOT_AGENT_BUDGET_SECONDS"])
        duration = re.search(r"--per-task-timeout (\d+) --max-steps (\d+)", self.workflow)
        self.assertIsNotNone(duration)
        self.assertTrue(10 <= budget < int(duration.group(1)) <= 900)
        self.assertTrue(2 <= int(duration.group(2)) <= 24)

    def test_scoring_requires_original_predictions_and_full_denominator(self):
        self.assertIn("princeton-nlp/SWE-bench_Lite", self.workflow)
        self.assertIn("score-predictions:", self.workflow)
        self.assertIn("prediction_count != '0'", self.workflow)
        self.assertIn("--dataset_name princeton-nlp/SWE-bench_Lite", self.workflow)
        self.assertIn("repopilot.swebench_results", self.workflow)
        self.assertIn("summary['evaluated'] != summary['submitted']", self.workflow)
        self.assertIn("summary['selected']", self.workflow)
        self.assertIn("model_predictions", self.workflow)
        self.assertIn("official-evaluation-result.json", self.workflow)
        self.assertNotIn("human_supplied_feedback", self.workflow)


if __name__ == "__main__":
    unittest.main()
