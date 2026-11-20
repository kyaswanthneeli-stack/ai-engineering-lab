import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repopilot.benchmark_batch import collect


class BenchmarkBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text("{}")
        self.tasks = [
            {"instance_id": f"sample__project-{n}",
             "repo": "sample/project",
             "base_commit": "a" * 40}
            for n in range(12)
        ]

    def test_only_real_model_proposals_exported(self):
        def fake_run(command, **kwargs):
            identifier = command[3]
            output = Path(command[command.index("--output")+1])
            output.mkdir(parents=True)
            if identifier.endswith("-0"):
                (output / "attempt.json").write_text(
                    json.dumps({"status": "model_patch_proposed"}))
                (output / "unreviewed-prediction.json").write_text(
                    json.dumps({
                        "instance_id": identifier,
                        "base_commit": "a" * 40,
                        "generated_by_model": True,
                        "model_name_or_path": "qwen-test",
                        "model_patch": "diff --git a/test.py b/test.py\n@@ -1 +1 @@\n-a\n+b\n",
                    }))
            else:
                (output / "attempt.json").write_text(
                    json.dumps({"status": "failed_model_attempt"}))
        with patch("repopilot.benchmark_batch.load_manifest",
                   return_value=self.tasks), patch(
                       "repopilot.benchmark_batch.subprocess.run",
                       side_effect=fake_run):
            result = collect(self.manifest, self.root / "output")
        self.assertEqual(result["selected_tasks"], 12)
        self.assertEqual(result["model_predictions"], 1)
        self.assertFalse(result["officially_evaluated"])
        predictions = (self.root / "output/predictions.jsonl").read_text().splitlines()
        self.assertEqual(len(predictions), 1)
        self.assertEqual(json.loads(predictions[0])["instance_id"],
                         "sample__project-0")

    def test_official_batch_workflow_uses_bounded_local_model(self):
        # Catch accidental removal of native Ollama or independent time limits.
        workflow=(Path(__file__).resolve().parents[2] /
                  ".github/workflows/repopilot-official-12-evaluation.yml")
        content=workflow.read_text(encoding="utf-8")
        # A costly 12-task benchmark must not auto-start for every PR branch.
        self.assertIn("push:\n    branches:\n      - main\n    paths:", content)
        for setting in (
                "REPOPILOT_OLLAMA_NATIVE: '1'",
                "REPOPILOT_PROVIDER_TIMEOUT_SECONDS: '110'",
                "REPOPILOT_AGENT_BUDGET_SECONDS: '270'",
                "--per-task-timeout 300",
                "python -m swebench.harness.run_evaluation"):
            with self.subTest(setting=setting):
                self.assertIn(setting,content)

    def test_corrupt_attempt_record_does_not_stop_later_predictions(self):
        def fake_run(command, **kwargs):
            identifier = command[3]
            output = Path(command[command.index("--output")+1])
            output.mkdir(parents=True)
            if identifier.endswith("-0"):
                (output / "attempt.json").write_text("{broken")
            elif identifier.endswith("-1"):
                (output / "attempt.json").write_text(
                    json.dumps({"status": "model_patch_proposed"}))
                (output / "unreviewed-prediction.json").write_text(json.dumps({
                    "instance_id": identifier,
                    "base_commit": "a" * 40,
                    "generated_by_model": True,
                    "model_name_or_path": "test-model",
                    "model_patch": "diff --git a/x.py b/x.py\\n@@ -1 +1 @@\\n-a\\n+b\\n",
                }))
            else:
                (output / "attempt.json").write_text(
                    json.dumps({"status": "failed_model_attempt"}))
        with patch("repopilot.benchmark_batch.load_manifest",
                   return_value=self.tasks), patch(
                       "repopilot.benchmark_batch.subprocess.run",
                       side_effect=fake_run):
            result = collect(self.manifest, self.root / "output")
        self.assertEqual(result["model_predictions"], 1)
        self.assertEqual(result["tasks"][0]["status"], "invalid_attempt_record")
        self.assertEqual(result["tasks"][0]["error_type"], "MalformedAttemptRecord")
        self.assertTrue(result["tasks"][1]["prediction_exported"])
        self.assertTrue((self.root / "output/summary.json").is_file())

    def test_malformed_prediction_evidence_is_a_recorded_failure(self):
        def fake_run(command, **kwargs):
            identifier = command[3]
            output = Path(command[command.index("--output")+1])
            output.mkdir(parents=True)
            (output / "attempt.json").write_text(json.dumps({
                "status": "model_patch_proposed" if identifier.endswith(("-0", "-1"))
                          else "failed_model_attempt"}))
            if identifier.endswith("-0"):
                (output / "unreviewed-prediction.json").write_text("{broken")
            elif identifier.endswith("-1"):
                (output / "unreviewed-prediction.json").write_text("[]")
        with patch("repopilot.benchmark_batch.load_manifest",
                   return_value=self.tasks), patch(
                       "repopilot.benchmark_batch.subprocess.run",
                       side_effect=fake_run):
            result = collect(self.manifest, self.root / "output")
        self.assertEqual(result["model_predictions"], 0)
        self.assertEqual(result["missing_predictions"], 12)
        for record in result["tasks"][:2]:
            self.assertEqual(record["status"], "invalid_model_prediction")
            self.assertEqual(record["error_type"], "MalformedPredictionEvidence")
        self.assertTrue((self.root / "output/summary.json").is_file())

    def test_timeout_is_unscored_and_does_not_create_prediction(self):
        with patch("repopilot.benchmark_batch.load_manifest",
                   return_value=self.tasks), patch(
                       "repopilot.benchmark_batch.subprocess.run",
                       side_effect=subprocess.TimeoutExpired("python", 30)):
            result = collect(self.manifest, self.root / "output")
        self.assertEqual(result["model_predictions"], 0)
        self.assertEqual(result["missing_predictions"], 12)
        self.assertTrue(all(x["status"] == "model_timeout" for x in result["tasks"]))
        self.assertIsNone(result["officially_resolved"])
        self.assertEqual((self.root / "output/predictions.jsonl").read_text(), "")


if __name__ == "__main__":
    unittest.main()
