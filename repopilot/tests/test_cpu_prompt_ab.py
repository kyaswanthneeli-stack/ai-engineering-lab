"""Contract tests for the small unscored issue-context A/B experiment."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repopilot.cpu_prompt_ab import (
    DJANGO, PYTEST, ORDER, compare_two_pinned_tasks,
)

DIFF = ("diff --git a/impl.py b/impl.py\n"
        "--- a/impl.py\n+++ b/impl.py\n"
        "@@ -1 +1 @@\n-def fixed(): return False\n"
        "+def fixed(): return True\n")


class CpuIssuePromptABTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text("{}")
        self.tasks = [
            {"instance_id": DJANGO, "repo": "django/django",
             "base_commit": "a" * 40},
            {"instance_id": PYTEST, "repo": "pytest-dev/pytest",
             "base_commit": "b" * 40},
        ]

    def simulate_model(self, invalid_patch=False):
        seen = []
        def invoke(command, **kwargs):
            cap = kwargs["env"]["REPOPILOT_ISSUE_CONTEXT_CHARS"]
            instance = command[3]
            assert cap in {"2500", "6500"}
            assert "--agentic" in command
            assert kwargs["timeout"] == 300
            assert kwargs["capture_output"] is True
            assert kwargs["check"] is False
            assert kwargs["text"] is True
            folder = Path(command[command.index("--output") + 1])
            folder.mkdir(parents=True, exist_ok=False)
            (folder / "attempt.json").write_text(json.dumps({
                "instance_id": instance,
                "status": "model_patch_proposed",
                "elapsed_ms": 900,
                "agent_steps": 3,
                "issue_context_chars": int(cap) - 1,
                "issue_context_trimmed": cap == "2500",
                "candidate_smoke": {"status": "inconclusive",
                                    "reason": "baseline_did_not_pass"},
            }))
            (folder / "unreviewed-prediction.json").write_text(json.dumps({
                "instance_id": instance,
                "base_commit": "a" * 40 if instance == DJANGO else "b" * 40,
                "generated_by_model": True,
                "human_reviewed": False,
                "model_name_or_path": "qwen2.5-coder:3b",
                "model_patch": "invalid" if invalid_patch else DIFF,
            }))
            seen.append((instance, int(cap), folder.name))
            return subprocess.CompletedProcess(command, 0, "", "")
        return seen, invoke

    def test_fixed_order_is_counterbalanced_and_only_two_tasks(self):
        self.assertEqual(ORDER, (
            (DJANGO, 6500), (PYTEST, 2500),
            (DJANGO, 2500), (PYTEST, 6500)))
        self.assertEqual(set(id for id, _ in ORDER), {DJANGO, PYTEST})

    def test_real_model_artifacts_and_fair_conditions_are_separate_from_solves(self):
        seen, runner = self.simulate_model()
        with patch("repopilot.cpu_prompt_ab.load_manifest",
                   return_value=self.tasks):
            result = compare_two_pinned_tasks(
                self.manifest, self.root / "run", run=runner)
        self.assertEqual(
            [(id, cap) for id, cap, _ in seen], list(ORDER))
        self.assertEqual(result["unique_selected_tasks"], 2)
        self.assertEqual(result["attempts"], 4)
        self.assertEqual(result["model_generated_patches"], 4)
        self.assertFalse(result["officially_evaluated"])
        self.assertIsNone(result["officially_resolved"])
        self.assertEqual(len(result["pairs"]), 2)
        self.assertTrue(all(x["officially_resolved"] is None
                            for x in result["records"]))
        self.assertTrue(all(x["short_issue_truncated"]
                            for x in result["pairs"]))
        self.assertTrue((self.root / "run/comparison.json").is_file())
        self.assertTrue((self.root / "run/progress.json").is_file())

    def test_unverifiable_model_patch_is_not_called_a_valid_prediction(self):
        _, runner = self.simulate_model(invalid_patch=True)
        with patch("repopilot.cpu_prompt_ab.load_manifest",
                   return_value=self.tasks):
            result = compare_two_pinned_tasks(
                self.manifest, self.root / "bad", run=runner)
        self.assertEqual(result["model_generated_patches"], 0)
        self.assertTrue(all(not x["model_generated_patch"]
                            for x in result["records"]))

    def test_outer_timeout_is_recorded_without_fabricated_prediction(self):
        def timeout(command, **kwargs):
            raise subprocess.TimeoutExpired(command, 300)
        with patch("repopilot.cpu_prompt_ab.load_manifest",
                   return_value=self.tasks):
            summary = compare_two_pinned_tasks(
                self.manifest, self.root / "timeouts", run=timeout)
        self.assertEqual(summary["model_generated_patches"], 0)
        self.assertTrue(all(row["process_status"] == "outer_timeout"
                            for row in summary["records"]))
        self.assertFalse(summary["officially_evaluated"])

    def test_refuse_to_overwrite_experiment_evidence(self):
        existing = self.root / "exists"
        existing.mkdir()
        with patch("repopilot.cpu_prompt_ab.load_manifest",
                   return_value=self.tasks):
            with self.assertRaisesRegex(ValueError, "overwrite"):
                compare_two_pinned_tasks(self.manifest, existing,
                                         run=lambda *args, **kwargs: None)

    def test_only_original_pinned_task_ids_are_allowed(self):
        with patch("repopilot.cpu_prompt_ab.load_manifest",
                   return_value=self.tasks[:1]):
            with self.assertRaisesRegex(ValueError, "original pinned"):
                compare_two_pinned_tasks(self.manifest, self.root / "missing")

    def test_reject_unbounded_task_timeout_and_steps(self):
        for timeout, steps in [(29,12),(901,12),(300,1),(300,25)]:
            with self.subTest(timeout=timeout,steps=steps):
                with self.assertRaisesRegex(ValueError, "safe bounds"):
                    compare_two_pinned_tasks(
                        self.manifest, self.root / "never",
                        per_task_timeout=timeout,max_steps=steps)


if __name__ == "__main__":
    unittest.main()
