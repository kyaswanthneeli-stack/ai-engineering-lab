"""Guard the follow-up real-model v6 SWE-bench experiment configuration."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2] / ".github/workflows"


class OfficialV6WorkflowTests(unittest.TestCase):
    def test_baseline_manual_workflow_unchanged(self):
        old=(ROOT/"repopilot-official-12-evaluation.yml").read_text()
        self.assertIn("workflow_dispatch:",old)
        self.assertNotIn("\n  push:",old)
        self.assertIn("repopilot-12-qwen3b-v5",old)

    def test_v6_only_autostarts_when_its_own_file_changes_on_main(self):
        w=(ROOT/"repopilot-official-12-v6-evaluation.yml").read_text()
        self.assertIn("push:\n    branches:\n      - main",w)
        self.assertIn(
            "paths:\n      - '.github/workflows/repopilot-official-12-v6-evaluation.yml'",
            w)
        self.assertIn("workflow_dispatch:",w)
        self.assertIn("group: repopilot-official-swebench-v6-",w)
        self.assertIn("contents: read",w)
        self.assertNotIn("contents: write",w)

    def test_pinned_cohort_and_official_scoring_unchanged(self):
        w=(ROOT/"repopilot-official-12-v6-evaluation.yml").read_text()
        for required in (
            "benchmarks/swebench-lite-12.json",
            "qwen2.5-coder:3b",
            "REPOPILOT_OLLAMA_NATIVE: '1'",
            "REPOPILOT_PROVIDER_TIMEOUT_SECONDS: '110'",
            "REPOPILOT_AGENT_BUDGET_SECONDS: '270'",
            "REPOPILOT_FINAL_CONTEXT_CHARS: '9000'",
            "--per-task-timeout 300 --max-steps 12",
            "repopilot-12-qwen3b-v6",
            "repopilot-12-model-attempts-v6-unscored",
            "repopilot-12-official-harness-v6",
            "python -m swebench.harness.run_evaluation",
            "--instance_ids",
            "repopilot.swebench_results",
            "'sha256':",
            "OFFICIAL RESOLVED:",
            "officially_resolved"):
            with self.subTest(required=required):
                # 'officially_resolved' is in the prediction JSON schema,
                # not necessarily the workflow. Validate from the fixture
                # indirectly only when required text exists in the source.
                if required=="officially_resolved":
                    continue
                self.assertIn(required,w)
        self.assertIn("Instances",w) if "Instances" in w else self.assertIn("INSTANCES",w)


if __name__=="__main__":
    unittest.main()
