import json
import tempfile
import unittest
from pathlib import Path
from repopilot.swebench_results import official_summary, EvaluationError, main as summary_main


class OfficialSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        p = Path(self.temp.name)
        self.manifest = p / "manifest.json"
        self.results = p / "results.json"
        self.predictions = p / "predictions.jsonl"
        self.ids = [f"project__repo-{n}" for n in range(12)]
        self.manifest.write_text(json.dumps({"tasks": [
            {"instance_id": x, "base_commit": "f" * 40} for x in self.ids
        ]}), encoding="utf-8")
        self.set_predictions(self.ids[:3])
        self.set_results([self.ids[0]], [self.ids[1]], [self.ids[2]])

    def set_predictions(self, ids):
        self.predictions.write_text("".join(json.dumps({
            "instance_id": x,
            "model_name_or_path": "test-model",
            "model_patch": "diff --git a/x.py b/x.py\n"
        })+"\n" for x in ids), encoding="utf-8")

    def set_results(self, resolved, unresolved, errors):
        self.results.write_text(json.dumps({
            "resolved_ids": resolved, "unresolved_ids": unresolved, "error_ids": errors
        }), encoding="utf-8")

    def test_partial_results_not_misrepresented_as_complete(self):
        data=official_summary(self.manifest, self.results, self.predictions)
        self.assertEqual(data["selected"], 12)
        self.assertEqual(data["evaluated"], 3)
        self.assertEqual(data["resolved"], 1)
        self.assertEqual(data["not_submitted"], 9)
        self.assertFalse(data["is_complete_12_task_evaluation"])
        self.assertEqual(data["resolved_over_evaluated"], 0.3333)
        self.assertEqual(data["resolved_over_selected"], 0.0833)

    def test_official_scorecard_cli_writes_validated_json(self):
        output=self.results.parent / "official-summary.json"
        summary_main([str(self.manifest), str(self.results),
                      str(self.predictions), "--output", str(output)])
        result=json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["selected"],12)
        self.assertEqual(result["submitted"],3)
        self.assertEqual(result["evaluated"],3)
        self.assertEqual(result["resolved"],1)
        self.assertEqual(result["not_submitted"],9)

    def test_official_workflow_publishes_validated_scoring_provenance(self):
        workflow=(Path(__file__).resolve().parents[2] /
                  ".github/workflows/repopilot-official-12-evaluation.yml")
        content=workflow.read_text(encoding="utf-8")
        for required in (
                "python -m repopilot.swebench_results",
                "official-summary.json",
                "provenance.json",
                "Incomplete official SWE-bench evidence",
                "sha256",
                "if: always()"):
            with self.subTest(required=required):
                self.assertIn(required,content)

    def test_unreported_submitted_tasks(self):
        self.set_results([self.ids[0]], [], [])
        data=official_summary(self.manifest, self.results, self.predictions)
        self.assertEqual(data["submitted_but_unreported"], 2)
        self.assertFalse(data["is_complete_12_task_evaluation"])

    def test_refuse_conflicting_categories(self):
        self.set_results([self.ids[0]], [self.ids[0]], [self.ids[2]])
        with self.assertRaises(EvaluationError):
            official_summary(self.manifest, self.results, self.predictions)

    def test_refuse_unsubmitted_result(self):
        self.set_results([self.ids[0], self.ids[3]], [], [])
        with self.assertRaises(EvaluationError):
            official_summary(self.manifest, self.results, self.predictions)

    def test_refuse_duplicate_predictions(self):
        self.set_predictions([self.ids[0], self.ids[0]])
        with self.assertRaises(EvaluationError):
            official_summary(self.manifest, self.results, self.predictions)

    def test_refuse_missing_harness_result(self):
        self.results.unlink()
        with self.assertRaises(EvaluationError):
            official_summary(self.manifest, self.results, self.predictions)

    def test_empty_evaluations_has_no_rate(self):
        self.predictions.write_text("")
        self.set_results([], [], [])
        data=official_summary(self.manifest, self.results, self.predictions)
        self.assertEqual(data["evaluated"], 0)
        self.assertIsNone(data["resolved_over_evaluated"])
        self.assertEqual(data["not_submitted"], 12)


if __name__ == "__main__":
    unittest.main()
