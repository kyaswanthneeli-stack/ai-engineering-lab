"""Keep CPU throughput preflight bounded, unassisted and separate from the cohort."""
import re
import unittest
from pathlib import Path

class CPUPreflightScopeTests(unittest.TestCase):
    def test_preflight_uses_single_pinned_task_and_not_human_assisted_retry(self):
        flow=(Path(__file__).resolve().parents[2] / ".github/workflows/repopilot-cpu-single-preflight.yml").read_text()
        self.assertIn("qwen2.5-coder:3b", flow)
        self.assertIn("REPOPILOT_PROVIDER_TIMEOUT_SECONDS: '120'",flow)
        self.assertIn("repopilot.benchmark_attempt django__django-12113",flow)
        self.assertIn("--agentic --max-steps 12",flow)
        self.assertIn("--manifest benchmarks/swebench-lite-12.json",flow)
        self.assertIn("repopilot.swebench_results import official_summary",flow)
        self.assertIn("not a new full-cohort score",flow)
        self.assertIn("provider.json",flow)
        self.assertIn("if: always()",flow)
        self.assertNotIn("ci/django_sqlite/retry.py",flow)
        self.assertNotIn("repopilot.benchmark_batch",flow)
        self.assertNotIn("human_supplied_feedback",flow)
        self.assertNotIn("packages: write",flow)
        self.assertNotIn("contents: write",flow)
