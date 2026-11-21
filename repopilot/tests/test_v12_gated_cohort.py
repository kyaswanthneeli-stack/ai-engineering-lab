"""Prevent an ungated or assisted full-cohort experiment."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FLOW = ROOT / ".github/workflows/repopilot-official-12-v12-3b-evaluation.yml"

class V12GatedCohortTests(unittest.TestCase):
    def test_requires_successful_independent_preflight_and_identical_source(self):
        flow = FLOW.read_text()
        for text in ("workflow_dispatch:", "github.ref == 'refs/heads/main'",
                     "verify-preflight:", "needs: verify-preflight",
                     "needs.verify-preflight.result == 'success'",
                     'summary["submitted"]==summary["evaluated"]==summary["resolved"]==1',
                     'result["resolved_ids"]==["django__django-12113"]',
                     "git diff --exit-code", "Model digest changed since verified preflight",
                     'actual["prediction_sha256"]==hashlib.sha256(pred).hexdigest()'):
            self.assertIn(text,flow)
        self.assertNotIn("  pull_request:",flow)
        self.assertNotIn("  push:",flow)

    def test_uniform_cohort_and_independent_score(self):
        flow=FLOW.read_text()
        generation=flow.split("  generate-predictions:",1)[1].split("  score-predictions:",1)[0]
        for text in ("REPOPILOT_MODEL: qwen2.5-coder:3b",
                     "REPOPILOT_COMPACT_DISCOVERY: '1'",
                     "REPOPILOT_COMPACT_FINAL: '1'",
                     "REPOPILOT_CONFIRM_RANKED_SOURCE: '1'",
                     "python -m repopilot.benchmark_batch",
                     "--manifest benchmarks/swebench-lite-12.json",
                     "Incomplete attempt evidence"):
            self.assertIn(text,generation)
        self.assertNotIn("django__django-12113",generation)
        self.assertNotIn("gh run download",generation)
        self.assertNotIn("ci/django_sqlite/retry.py",generation)
        self.assertIn("summary['selected'] != 12",flow)
        self.assertIn("summary['error']",flow)
