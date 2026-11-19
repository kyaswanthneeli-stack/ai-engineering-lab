import json
import tempfile
import unittest
from pathlib import Path

from repopilot.benchmark_compare import compare_official_runs
from repopilot.swebench_results import EvaluationError


class BenchmarkComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.manifest=root/"manifest.json"
        self.baseline_results=root/"baseline-score.json"
        self.baseline_predictions=root/"baseline-predictions.jsonl"
        self.candidate_results=root/"candidate-score.json"
        self.candidate_predictions=root/"candidate-predictions.jsonl"
        self.ids=[f"project__repo-{i}" for i in range(4)]
        self.manifest.write_text(json.dumps({"tasks":[
            {"instance_id":name,"base_commit":"a"*40} for name in self.ids]}))
        self.predictions(self.baseline_predictions,self.ids[:3])
        self.results(self.baseline_results,[self.ids[0]],[self.ids[1],self.ids[2]],[])
        self.predictions(self.candidate_predictions,self.ids[0:2])
        self.results(self.candidate_results,[self.ids[1]],[self.ids[0]],[])

    def predictions(self,path,ids):
        rows=[{"instance_id":item,
               "model_name_or_path":"fake-test-model",
               "model_patch":"diff --git a/x.py b/x.py\n"} for item in ids]
        path.write_text("".join(json.dumps(row)+"\n" for row in rows))

    def results(self,path,resolved,unresolved,errors):
        path.write_text(json.dumps({
            "resolved_ids":resolved,"unresolved_ids":unresolved,"error_ids":errors}))

    def compare(self):
        return compare_official_runs(
            self.manifest,self.baseline_results,self.baseline_predictions,
            self.candidate_results,self.candidate_predictions)

    def test_only_common_officially_evaluated_tasks_are_compared(self):
        outcome=self.compare()
        self.assertEqual(outcome["selected_tasks"],4)
        self.assertEqual(outcome["baseline_officially_evaluated"],3)
        self.assertEqual(outcome["candidate_officially_evaluated"],2)
        self.assertEqual(outcome["comparable_officially_evaluated"],2)
        self.assertEqual(outcome["newly_resolved"],[self.ids[1]])
        self.assertEqual(outcome["regressed"],[self.ids[0]])
        self.assertEqual(outcome["resolved_delta_on_comparable"],0)
        self.assertFalse(next(x for x in outcome["per_task"]
                              if x["instance_id"]==self.ids[2])["directly_comparable"])

    def test_missing_evaluator_result_is_not_success(self):
        self.candidate_results.unlink()
        with self.assertRaises(EvaluationError):
            self.compare()

    def test_no_common_evaluated_instances_returns_no_delta(self):
        self.predictions(self.candidate_predictions,[self.ids[3]])
        self.results(self.candidate_results,[self.ids[3]],[],[])
        summary=self.compare()
        self.assertEqual(summary["comparable_officially_evaluated"],0)
        self.assertIsNone(summary["resolved_delta_on_comparable"])

    def test_reject_mismatched_prediction_and_evaluation(self):
        self.results(self.candidate_results,[self.ids[3]],[],[])
        with self.assertRaises(EvaluationError):
            self.compare()


if __name__=="__main__":
    unittest.main()
