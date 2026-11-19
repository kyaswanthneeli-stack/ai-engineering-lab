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
        self.assertEqual(result["attempt_status_counts"], {
            "failed_model_attempt": 11, "model_patch_proposed": 1})
        self.assertEqual(result["failed_model_attempt_without_patch"], 11)
        self.assertEqual(result["timeout_without_patch"], 0)
        self.assertFalse(result["officially_evaluated"])
        predictions = (self.root / "output/predictions.jsonl").read_text().splitlines()
        self.assertEqual(len(predictions), 1)
        self.assertEqual(json.loads(predictions[0])["instance_id"],
                         "sample__project-0")

    def test_subset_uses_original_manifest_and_attempts_only_requested_ids(self):
        called=[]
        def fake_run(command, **kwargs):
            identifier=command[3]
            called.append(identifier)
            self.assertEqual(
                command[command.index("--manifest")+1],str(self.manifest))
            output=Path(command[command.index("--output")+1])
            output.mkdir(parents=True)
            (output/"attempt.json").write_text(
                json.dumps({"status":"failed_model_attempt"}))
        with patch("repopilot.benchmark_batch.load_manifest",
                   return_value=self.tasks), patch(
                       "repopilot.benchmark_batch.subprocess.run",
                       side_effect=fake_run):
            result=collect(
                self.manifest,self.root/"subset",
                instance_ids=["sample__project-11","sample__project-0"])
        self.assertEqual(called,["sample__project-0","sample__project-11"])
        self.assertEqual(result["selected_tasks"],2)
        self.assertEqual(result["pinned_manifest_tasks"],12)
        self.assertEqual(result["missing_predictions"],2)
        self.assertFalse(result["officially_evaluated"])

    def test_reject_nonmanifest_duplicate_or_empty_pilot_selection(self):
        with patch("repopilot.benchmark_batch.load_manifest",
                   return_value=self.tasks):
            for selection in ([],["sample__project-2","sample__project-2"],
                              ["not-pinned__project-4"]):
                with self.subTest(selection=selection):
                    with self.assertRaisesRegex(ValueError,"unique nonempty IDs"):
                        collect(self.manifest,self.root/"never-created",
                                instance_ids=selection)
            self.assertFalse((self.root/"never-created").exists())

    def test_model_provider_failure_counted_but_never_called_solved(self):
        def fake_run(command,**kwargs):
            output=Path(command[command.index("--output")+1])
            output.mkdir(parents=True)
            (output/"attempt.json").write_text(json.dumps({
                "status":"provider_unavailable",
                "error_type":"ProviderTransportError",
                "failure_category":"model_transport"}))
        with patch("repopilot.benchmark_batch.load_manifest",
                   return_value=self.tasks),patch(
                       "repopilot.benchmark_batch.subprocess.run",
                       side_effect=fake_run):
            result=collect(self.manifest,self.root/"provider")
        self.assertEqual(result["attempt_status_counts"],{"provider_unavailable":12})
        self.assertEqual(result["provider_unavailable_without_patch"],12)
        self.assertEqual(result["missing_predictions"],12)
        self.assertIsNone(result["officially_resolved"])
        self.assertFalse(result["officially_evaluated"])
        self.assertTrue(all(t["failure_category"]=="model_transport"
                            for t in result["tasks"]))

    def test_timeout_is_unscored_and_does_not_create_prediction(self):
        with patch("repopilot.benchmark_batch.load_manifest",
                   return_value=self.tasks), patch(
                       "repopilot.benchmark_batch.subprocess.run",
                       side_effect=subprocess.TimeoutExpired("python", 30)):
            result = collect(self.manifest, self.root / "output")
        self.assertEqual(result["model_predictions"], 0)
        self.assertEqual(result["missing_predictions"], 12)
        self.assertEqual(result["attempt_status_counts"], {"model_timeout":12})
        self.assertEqual(result["timeout_without_patch"],12)
        self.assertEqual(result["failed_model_attempt_without_patch"],0)
        self.assertTrue(all(x["status"] == "model_timeout" for x in result["tasks"]))
        self.assertIsNone(result["officially_resolved"])
        self.assertEqual((self.root / "output/predictions.jsonl").read_text(), "")


if __name__ == "__main__":
    unittest.main()
