"""Check that the preserved v10 verdicts reconcile with the pinned cohort."""
import hashlib
import json
import unittest
from pathlib import Path


class PublishedV10EvidenceTests(unittest.TestCase):
    def test_preserved_results_match_the_pinned_manifest(self):
        directory = Path(__file__).resolve().parents[1] / "benchmarks"
        manifest_bytes = (directory / "swebench-lite-12.json").read_bytes()
        evidence = json.loads((directory / "evidence/v10-audited-evidence.json").read_text())
        expected_hash = evidence["provenance"]["sha256"]["manifest"]
        self.assertEqual(hashlib.sha256(manifest_bytes).hexdigest(), expected_hash)

        selected_ids = [task["instance_id"] for task in json.loads(manifest_bytes)["tasks"]]
        attempts = evidence["generation_attempts"]
        self.assertCountEqual([attempt["instance_id"] for attempt in attempts], selected_ids)
        submitted_ids = [attempt["instance_id"] for attempt in attempts
                         if attempt["generation_status"] == "model_patch_proposed"]
        result = evidence["official_result"]
        self.assertCountEqual(result["submitted_ids"], submitted_ids)
        self.assertCountEqual(result["completed_ids"], submitted_ids)
        verdicts = result["resolved_ids"] + result["unresolved_ids"] + result["error_ids"]
        self.assertCountEqual(verdicts, result["completed_ids"])

        summary = evidence["summary"]
        self.assertEqual((summary["selected"], summary["submitted"], summary["evaluated"]),
                         (len(selected_ids), len(submitted_ids), len(verdicts)))
        self.assertEqual(summary["not_submitted"], len(selected_ids) - len(submitted_ids))
        self.assertEqual(summary["resolved"], len(result["resolved_ids"]))
        self.assertEqual(summary["unresolved"], len(result["unresolved_ids"]))
        self.assertEqual(summary["error"], len(result["error_ids"]))
        self.assertEqual((summary["resolved"], summary["selected"]), (1, 12))
