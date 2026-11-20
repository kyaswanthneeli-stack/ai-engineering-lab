"""Static safety and comparability gate for the one-time official v9 retest.

The workflow runs real model inference and independently scores only submitted
patches. These unit tests alone do not validate benchmark resolution.
"""
import unittest
from pathlib import Path


class V9OfficialWorkflowGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = (Path(__file__).resolve().parents[2] /
                        ".github/workflows/repopilot-official-12-v9-evaluation.yml"
                        ).read_text(encoding="utf-8")

    def test_only_main_merge_of_own_file_triggers_automatic_run(self):
        content = self.workflow
        self.assertIn("workflow_dispatch:", content)
        self.assertIn("  push:\n    branches:\n      - main\n    paths:", content)
        self.assertIn(
            "- '.github/workflows/repopilot-official-12-v9-evaluation.yml'",
            content)
        self.assertNotIn("\n  schedule:", content)
        self.assertNotIn("\n  pull_request:", content)

    def test_true_model_and_official_harness_remain_required(self):
        content = self.workflow
        for literal in (
            "REPOPILOT_MODEL: qwen2.5-coder:3b",
            "REPOPILOT_OLLAMA_NATIVE: '1'",
            "REPOPILOT_PROVIDER_TIMEOUT_SECONDS: '110'",
            "REPOPILOT_AGENT_BUDGET_SECONDS: '270'",
            "REPOPILOT_FINAL_CONTEXT_CHARS: '9000'",
            "REPOPILOT_CANDIDATE_SMOKE: '1'",
            "REPOPILOT_CANDIDATE_SMOKE_IMAGE: repopilot-candidate-deps:py310",
            "docker build --pull -t repopilot-candidate-deps:py310 -f ci/Dockerfile.candidate-smoke ci",
            "--manifest benchmarks/swebench-lite-12.json",
            "--per-task-timeout 300 --max-steps 12",
            "python -m swebench.harness.run_evaluation",
            "--run_id repopilot-12-qwen3b-v9",
            "python -m repopilot.swebench_results",
        ):
            with self.subTest(literal=literal):
                self.assertIn(literal, content)
        self.assertIn("actions/setup-python@v6", content)
        self.assertNotIn("actions/setup-python@v9", content)

    def test_artifacts_and_scores_are_separate_and_v9_only(self):
        content = self.workflow
        for literal in (
            "repopilot-12-model-attempts-v9-unscored",
            "repopilot-12-official-harness-v9",
            "official-summary.json",
            "provenance.json",
            "prediction_count != '0'",
            "Incomplete official SWE-bench evidence",
            "'resolved': summary['resolved']",
            "'evaluated': summary['evaluated']",
        ):
            with self.subTest(literal=literal):
                self.assertIn(literal, content)
        self.assertNotIn("repopilot-12-qwen3b-v6", content)


if __name__ == "__main__":
    unittest.main()
