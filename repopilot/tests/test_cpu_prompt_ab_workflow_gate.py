"""CI guard: A/B workflow may run only after exact independent v9 scoring."""
import unittest
from pathlib import Path


class CpuPromptABWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flow = (
            Path(__file__).resolve().parents[2] /
            ".github/workflows/repopilot-cpu-prompt-ab-after-v9.yml"
        ).read_text(encoding="utf-8")

    def test_v9_run_completion_and_source_commit_gate(self):
        s = self.flow
        for token in (
            "workflow_run:",
            "RepoPilot official v9 12-task SWE-bench evaluation",
            "github.event.workflow_run.id == 44776554310",
            "github.event.workflow_run.conclusion == 'success'",
            "5ffdcd5695fc2df32fef40d0e388a04798f4dee7",
            "actions/download-artifact@v4",
            "name: repopilot-12-official-harness-v9",
            "run-id: 44776554310",
            "official-summary.json",
            "provenance.json",
            "official-evaluation-result.json",
            "hashlib.sha256",
            "summary['evaluated']==summary['submitted']",
        ):
            with self.subTest(token=token):
                self.assertIn(token, s)
        self.assertNotIn("\n  push:", s)
        self.assertNotIn("\n  pull_request:", s)
        self.assertNotIn("\n  schedule:", s)

    def test_two_tasks_and_no_official_evaluator_are_intentional(self):
        s = self.flow
        for token in (
            "django__django-12113",
            "pytest-dev__pytest-11148",
            "python -m repopilot.cpu_prompt_ab",
            "--per-task-timeout 300 --max-steps 12",
            "unique_selected_tasks",
            "officially_resolved",
            "officially_evaluated",
            "UNSCORED EXPERIMENT",
        ):
            with self.subTest(token=token):
                self.assertIn(token, s)
        self.assertNotIn("python -m swebench.harness.run_evaluation", s)
        self.assertNotIn("repopilot-official-12-v10-evaluation.yml", s)

    def test_model_and_sandbox_settings_match_v9(self):
        s = self.flow
        for token in (
            "REPOPILOT_MODEL: qwen2.5-coder:3b",
            "REPOPILOT_OLLAMA_NATIVE: '1'",
            "REPOPILOT_MAX_TOKENS: '1200'",
            "REPOPILOT_PROVIDER_TIMEOUT_SECONDS: '110'",
            "REPOPILOT_AGENT_BUDGET_SECONDS: '270'",
            "REPOPILOT_FINAL_CONTEXT_CHARS: '9000'",
            "REPOPILOT_CANDIDATE_SMOKE: '1'",
            "REPOPILOT_CANDIDATE_SMOKE_IMAGE: repopilot-candidate-deps:py310",
            "docker build --pull -t repopilot-candidate-deps:py310",
            "repopilot-cpu-prompt-ab-after-v9",
            "actions/upload-artifact@v4",
        ):
            with self.subTest(token=token):
                self.assertIn(token, s)
        self.assertNotIn("GITHUB_TOKEN: ", s)


if __name__ == "__main__":
    unittest.main()
