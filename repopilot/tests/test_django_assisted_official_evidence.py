"""Pin the original assisted Django result without inflating full-cohort scores."""
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "benchmarks/evidence/django-12113-assisted-7b-2026-11-21"


class DjangoAssistedOfficialEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provenance = json.loads((EVIDENCE / "provenance.json").read_text())
        cls.official_bytes = (EVIDENCE / "official.json").read_bytes()
        cls.prediction_bytes = (EVIDENCE / "predictions.jsonl").read_bytes()
        cls.official = json.loads(cls.official_bytes)
        cls.prediction = json.loads(cls.prediction_bytes)

    def test_original_artifact_hashes_match_provenance(self):
        self.assertEqual(hashlib.sha256(self.official_bytes).hexdigest(),
                         self.provenance["official_result_sha256"])
        self.assertEqual(hashlib.sha256(self.prediction_bytes).hexdigest(),
                         self.provenance["prediction_sha256"])
        self.assertEqual(self.provenance["source_branch_commit"],
                         "6aaf3fa1e9ad0780ac5a5e7c4aed1ee930d2bee0")
        self.assertEqual(self.provenance["run_id"], 44910644263)
        self.assertEqual(self.prediction_bytes.count(b"\n"), 1)

    def test_official_single_task_resolution_is_not_a_full_cohort_result(self):
        task = "django__django-12113"
        self.assertEqual(self.official["schema_version"], 2)
        self.assertEqual(self.official["total_instances"], 1)
        self.assertEqual(self.official["submitted_instances"], 1)
        self.assertEqual(self.official["completed_instances"], 1)
        self.assertEqual(self.official["resolved_instances"], 1)
        self.assertEqual(self.official["error_instances"], 0)
        self.assertEqual(self.official["unresolved_instances"], 0)
        self.assertEqual(self.official["submitted_ids"], [task])
        self.assertEqual(self.official["resolved_ids"], [task])
        self.assertEqual(self.prediction["instance_id"], task)
        self.assertEqual(self.prediction["model_name_or_path"], "qwen2.5-coder:7b")
        self.assertEqual(self.provenance["evidence_type"],
                         "independent_official_evaluation_of_human_assisted_single_task")

    def test_scored_patch_and_base_commit_match_pinned_public_issue(self):
        self.assertEqual(hashlib.sha256(
            self.prediction["model_patch"].encode("utf-8")).hexdigest(),
            self.provenance["patch_sha256"])
        self.assertIn("sig.append(test_database_name)", self.prediction["model_patch"])
        self.assertIn("sig.append(self.connection.alias)", self.prediction["model_patch"])
        manifest = json.loads((ROOT / "benchmarks/swebench-lite-12.json").read_text())
        matches = [item for item in manifest["tasks"]
                   if item["instance_id"] == self.prediction["instance_id"]]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["base_commit"], self.provenance["base_commit"])
        self.assertEqual(len(manifest["tasks"]), 12)
        self.assertTrue(all(code == 0 for code in
                            self.provenance["local_probes"].values()))


if __name__ == "__main__":
    unittest.main()
