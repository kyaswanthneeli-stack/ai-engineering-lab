"""Permanent integrity checks for Nov 20 official SWE-bench Lite results.

Patch hashes were calculated from original GitHub Actions artifact #14616122611.
This is a faithful record of a six-submission partial evaluation, not 12/12.
"""
from hashlib import sha256
import json
from pathlib import Path
import unittest

from repopilot.swebench_results import official_summary

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
ORIGINAL_PATCH_SHA256 = {
    "sympy__sympy-14774": "1211de2e15497ac6e87d2e895d4978d6fe7722637c16dd13b33077e3a46eb0fc",
    "django__django-12113": "ea1643e025ac3004910b40b452131c042c339b7ffc93894417ad406886fac9af",
    "pydata__xarray-4493": "db047c3fcd194fbfabc0d0d848980e5f748c9846678623792f2e1707004d71d2",
    "scikit-learn__scikit-learn-12471": "976953597bedf3bdf795fc3aa0c16e799a1afdac688b8274a28ee6876c9a9e2a",
    "django__django-12125": "e62733e61ac5dbdba259f410d54deb484f3fe49fc33cf80911e0840b49407299",
    "matplotlib__matplotlib-22835": "7a990df62b24ae778bd6281a7390985001e5ecf9e66b8a7999bfa38391ae661f",
}


class Nov20PublishedBenchmarkEvidenceTests(unittest.TestCase):
    def test_republished_model_patches_match_original_artifact(self):
        rows = [json.loads(line) for line in
                (BENCHMARKS / "official-predictions-2026-11-20.jsonl")
                .read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(rows), 6)
        hashes = {r["instance_id"]:
                  sha256(r["model_patch"].encode("utf-8")).hexdigest()
                  for r in rows}
        self.assertEqual(hashes, ORIGINAL_PATCH_SHA256)
        self.assertEqual({r["model_name_or_path"] for r in rows},
                         {"qwen2.5-coder:3b"})

    def test_official_harness_counts_and_missing_tasks(self):
        result = official_summary(
            BENCHMARKS / "swebench-lite-12.json",
            BENCHMARKS / "official-score-2026-11-20.json",
            BENCHMARKS / "official-predictions-2026-11-20.jsonl")
        self.assertEqual(result["selected"], 12)
        self.assertEqual(result["submitted"], 6)
        self.assertEqual(result["evaluated"], 6)
        self.assertEqual(result["resolved"], 1)
        self.assertEqual(result["unresolved"], 5)
        self.assertEqual(result["error"], 0)
        self.assertEqual(result["not_submitted"], 6)
        self.assertEqual(result["resolved_over_evaluated"], 0.1667)
        self.assertEqual(result["resolved_over_selected"], 0.0833)
        self.assertFalse(result["is_complete_12_task_evaluation"])
        raw = json.loads(
            (BENCHMARKS / "official-score-2026-11-20.json").read_text())
        self.assertEqual(raw["resolved_ids"], ["sympy__sympy-14774"])


if __name__ == "__main__":
    unittest.main()
