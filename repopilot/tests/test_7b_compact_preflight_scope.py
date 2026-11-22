"""Protect the isolated stronger-model preflight from accidental assisted evaluation."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WF=ROOT/".github/workflows/repopilot-7b-compact-preflight.yml"

class StrongerModelPreflightTests(unittest.TestCase):
    def test_model_and_budgets(self):
        text=WF.read_text()
        for value in ("qwen2.5-coder:7b","REPOPILOT_COMPACT_DISCOVERY: '1'",
                      "REPOPILOT_COMPACT_FINAL: '1'",
                      "REPOPILOT_AGENT_BUDGET_SECONDS: '720'",
                      "REPOPILOT_FINAL_CONTEXT_CHARS: '6000'",
                      "timeout 840s","REPOPILOT_PROVIDER_TIMEOUT_SECONDS: '120'",
                      "contents: read","persist-credentials: false"):
            self.assertIn(value,text)
        self.assertNotIn("qwen2.5-coder:3b",text)
    def test_unassisted_scope_and_independent_evaluator(self):
        text=WF.read_text()
        for value in ("bench/repopilot-7b-compact-preflight",
                      "python -m repopilot.benchmark_attempt django__django-12113",
                      "--agentic --max-steps 12 --manifest benchmarks/swebench-lite-12.json",
                      "candidate.get(\"generated_by_model\") is True",
                      "swebench.harness.run_evaluation",
                      'result["submitted"]==result["evaluated"]==1',
                      'result["error"]==0',"not a new full-cohort score"):
            self.assertIn(value,text)
        for value in ("required_targets=", "exact_edit_anchors=", "ci/django_sqlite/retry.py", "REPOPILOT_API_KEY", "contents: write"):
            self.assertNotIn(value,text)
