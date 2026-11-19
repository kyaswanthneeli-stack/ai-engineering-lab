"""Regression guard for the immutable published November 19 official result.

Checks original model-patch SHA256s against the recovered workflow artifact.
This does not re-run the evaluator or establish wider model reliability.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import unittest

from repopilot.swebench_results import official_summary


BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
ORIGINAL_PATCH_SHA256 = {
    "sympy__sympy-14774": "1211de2e15497ac6e87d2e895d4978d6fe7722637c16dd13b33077e3a46eb0fc",
    "sympy__sympy-13773": "5878dc3e0d524e667fba4be1a3352d3429ebd3dccc78d3f7e48e422499c9a2ec",
    "django__django-12113": "ea1643e025ac3004910b40b452131c042c339b7ffc93894417ad406886fac9af",
    "pydata__xarray-4493": "db047c3fcd194fbfabc0d0d848980e5f748c9846678623792f2e1707004d71d2",
    "django__django-12125": "e62733e61ac5dbdba259f410d54deb484f3fe49fc33cf80911e0840b49407299",
    "matplotlib__matplotlib-22835": "7a990df62b24ae778bd6281a7390985001e5ecf9e66b8a7999bfa38391ae661f",
}


class PublishedOfficialEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = BENCHMARKS / "swebench-lite-12.json"
        cls.results = BENCHMARKS / "official-score-2026-11-19.json"
        cls.predictions = BENCHMARKS / "official-predictions-2026-11-19.jsonl"

    def test_submitted_patches_match_original_downloaded_artifact(self):
        rows = [json.loads(line) for line in self.predictions.read_text().splitlines()
                if line.strip()]
        self.assertEqual(len(rows), 6)
        actual = {row["instance_id"]:
                  sha256(row["model_patch"].encode("utf-8")).hexdigest()
                  for row in rows}
        self.assertEqual(actual, ORIGINAL_PATCH_SHA256)
        self.assertEqual({row["model_name_or_path"] for row in rows},
                         {"qwen2.5-coder:3b"})

    def test_recorded_results_match_submissions_and_pinned_manifest(self):
        report = official_summary(self.manifest, self.results, self.predictions)
        self.assertEqual(report["selected"], 12)
        self.assertEqual(report["submitted"], 6)
        self.assertEqual(report["evaluated"], 6)
        self.assertEqual(report["resolved"], 1)
        self.assertEqual(report["unresolved"], 5)
        self.assertEqual(report["error"], 0)
        self.assertEqual(report["not_submitted"], 6)
        self.assertEqual(report["submitted_but_unreported"], 0)
        self.assertEqual(report["resolved_over_evaluated"], 0.1667)
        self.assertEqual(report["resolved_over_selected"], 0.0833)
        self.assertFalse(report["is_complete_12_task_evaluation"])
        source = json.loads(self.results.read_text())
        self.assertEqual(source["resolved_ids"], ["sympy__sympy-14774"])


if __name__ == "__main__":
    unittest.main()
