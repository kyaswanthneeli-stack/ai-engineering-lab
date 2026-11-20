"""Replay evidence checks and isolation, using explicitly synthetic fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

SPEC = importlib.util.spec_from_file_location(
    "v9_replay", Path(__file__).resolve().parents[1] / "ci/replay_v9_smoke.py")
replay_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay_module)


class SmokeReplayTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        source_manifest = Path(__file__).resolve().parents[1] / "benchmarks/swebench-lite-12.json"
        self.manifest = self.root / "manifest.json"
        self.manifest.write_bytes(source_manifest.read_bytes())
        self.tasks = replay_module.load_manifest(self.manifest)
        selected = list(replay_module.SELECTED)
        selected += [t["instance_id"] for t in self.tasks if t["instance_id"] not in selected][:2]
        proposal = ("diff --git a/value.py b/value.py\n--- a/value.py\n+++ b/value.py\n"
                    "@@ -1 +1 @@\n-value = 1\n+value = 2\n")
        predictions = [{"instance_id": i, "model_name_or_path": "synthetic-fixture",
                        "model_patch": proposal} for i in selected]
        (self.evidence / "real-model-predictions.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in predictions))
        (self.evidence / "official-evaluation-result.json").write_text(json.dumps({
            "resolved_ids": selected[:1], "unresolved_ids": selected[1:], "error_ids": []}))
        summary = replay_module.official_summary(self.manifest,
            self.evidence / "official-evaluation-result.json",
            self.evidence / "real-model-predictions.jsonl")
        (self.evidence / "official-summary.json").write_text(json.dumps(summary))
        provenance = {"commit_sha": replay_module.SOURCE,
                      "harness_run_id": "repopilot-12-qwen3b-v9",
                      "github_run_url": "https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44776554310",
                      "sha256": {}}
        for key, path in {"manifest": self.manifest,
                          "model_predictions": self.evidence / "real-model-predictions.jsonl",
                          "official_results": self.evidence / "official-evaluation-result.json",
                          "validated_summary": self.evidence / "official-summary.json"}.items():
            provenance["sha256"][key] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.evidence / "provenance.json").write_text(json.dumps(provenance))
        self.rows = [{**t, "problem_statement": "Public issue only",
                      "patch": "PRIVATE_GOLD_NOT_ALLOWED", "test_patch": "PRIVATE_TEST_NOT_ALLOWED"}
                     for t in self.tasks]

    def checkout(self, url, commit, destination):
        self.assertTrue(url.startswith("https://github.com/"))
        self.assertIn(commit, [t["base_commit"] for t in self.tasks])
        destination.mkdir()
        (destination / "value.py").write_text("value = 1\n")
        return destination

    def test_four_case_replay_has_no_gold_or_official_resolution_claim(self):
        observed = []
        def checker(repo, proposal, issue, timeout):
            observed.append(issue)
            self.assertEqual(issue, "Public issue only")
            self.assertNotIn("PRIVATE_", proposal)
            self.assertEqual((repo / "value.py").read_text(), "value = 1\n")
            return {"status": "inconclusive", "baseline_failure_category": "import_error"}
        result = replay_module.replay(self.manifest, self.evidence,
            self.root / "output", label="synthetic-unit-test",
            dataset_loader=lambda: self.rows, checkout=self.checkout, checker=checker)
        self.assertEqual(len(observed), 4)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["usable_smoke_baselines"], 0)
        self.assertIsNone(result["officially_resolved"])
        self.assertFalse(result["officially_evaluated"])
        self.assertNotIn("PRIVATE_", json.dumps(result))

    def test_tampered_prediction_fails_before_checkout(self):
        with (self.evidence / "real-model-predictions.jsonl").open("a") as file:
            file.write("tampered")
        checkout = Mock()
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            replay_module.replay(self.manifest, self.evidence, self.root / "output",
                label="test", dataset_loader=lambda: self.rows, checkout=checkout)
        checkout.assert_not_called()

    def test_wrong_dataset_revision_fails_before_checkout(self):
        rows = [{**row, "base_commit": "0" * 40} for row in self.rows]
        checkout = Mock()
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            replay_module.replay(self.manifest, self.evidence, self.root / "output",
                label="test", dataset_loader=lambda: rows, checkout=checkout)
        checkout.assert_not_called()

    def test_existing_evidence_is_not_overwritten(self):
        output = self.root / "output"
        output.mkdir()
        (output / "summary.json").write_text("preserve")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            replay_module.replay(self.manifest, self.evidence, output, label="test")
        self.assertEqual((output / "summary.json").read_text(), "preserve")
