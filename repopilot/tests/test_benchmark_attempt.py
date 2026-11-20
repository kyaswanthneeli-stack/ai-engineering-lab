import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from repopilot.benchmark_attempt import attempt_one,main,bounded_issue_context,configured_issue_context_chars

SHA="a"*40
INSTANCE="sample__repo-123"
class AttemptsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.manifest=self.root/"manifest.json"
        self.manifest.write_text(json.dumps({"tasks":[
            {"instance_id":f"sample__repo-{i}","repo":"sample/repo","base_commit":SHA}
            for i in range(123,135)
        ]}))
    def dataset(self):
        return [{"instance_id":INSTANCE,"repo":"sample/repo",
                 "base_commit":SHA,"problem_statement":"Fix the bug in main.py"}]
    def checkout(self,url,sha,path):
        self.assertEqual(sha,SHA)
        path.mkdir()
        (path/"main.py").write_text("def bug():return 1\n")
        return path
    def proposed(self,*args):
        class Spec:
            patch="diff --git a/main.py b/main.py\n--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n-def bug():return 1\n+def bug():return 2\n"
        return Spec(),{"model":"mock-coder","provider_reported_usage_by_attempt":[{"total_tokens":10}]}

    def test_long_real_issue_bounded_for_cpu_model_without_fabricated_patch(self):
        statement="Root cause and expected behavior.\n"+("middle details\n"*1600)+"\nFINAL REPRODUCTION CODE"
        excerpt=bounded_issue_context(statement)
        self.assertLessEqual(len(excerpt),6500)
        self.assertTrue(excerpt.startswith("Root cause and expected behavior."))
        self.assertIn("FINAL REPRODUCTION CODE",excerpt)
        self.assertLess(len(excerpt),len(statement))
        self.assertIn("middle of long issue omitted",excerpt)
        self.assertEqual(bounded_issue_context("short"),"short")

    def test_reject_unbounded_issue_context_request(self):
        with self.assertRaises(ValueError):
            bounded_issue_context("issue",50000)

    def test_records_real_model_patch_as_unreviewed_not_resolved(self):
        output=self.root/"run"
        result=attempt_one(self.manifest,INSTANCE,output,dataset_loader=self.dataset,
                           checkout=self.checkout,model_proposer=self.proposed,
                           model="mock-coder",url="http://127.0.0.1:11434/v1")
        self.assertEqual(result["status"],"model_patch_proposed")
        self.assertIsNone(result["officially_resolved"])
        self.assertFalse(result["officially_evaluated"])
        patch=json.loads((output/"unreviewed-prediction.json").read_text())
        self.assertFalse(patch["human_reviewed"])
        self.assertTrue(patch["generated_by_model"])
    def test_cpu_issue_context_opt_in_preserves_head_tail_and_provenance(self):
        statement=("Important repro: source semantics changed.\\n" +
                   "intermediate trace details\\n" * 700 +
                   "FINAL REPRODUCTION: preserve expected output")
        captured=[]
        def proposer(work, issue, *args):
            captured.append(issue)
            return self.proposed()
        row={"instance_id":INSTANCE,"repo":"sample/repo",
             "base_commit":SHA,"problem_statement":statement}
        with patch.dict("os.environ",
                        {"REPOPILOT_ISSUE_CONTEXT_CHARS":"3500"}):
            report=attempt_one(
                self.manifest,INSTANCE,self.root/"cpu-limited",
                dataset_loader=lambda:[row],checkout=self.checkout,
                model_proposer=proposer)
        self.assertEqual(report["status"],"model_patch_proposed")
        self.assertEqual(report["issue_context_limit_chars"],3500)
        self.assertEqual(report["issue_context_chars"],len(captured[0]))
        self.assertLessEqual(len(captured[0]),3500)
        self.assertTrue(report["issue_context_trimmed"])
        self.assertTrue(captured[0].startswith("Important repro:"))
        self.assertIn("FINAL REPRODUCTION",captured[0])
        self.assertIn("middle of long issue omitted",captured[0])
        self.assertFalse(report["officially_evaluated"])
        self.assertIsNone(report["officially_resolved"])

    def test_cpu_issue_context_default_is_backward_compatible(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(configured_issue_context_chars(),6500)

    def test_cpu_issue_context_rejects_invalid_limits(self):
        for raw in ("100","1000","2499","6501","100000","bad","3.5",""):
            with self.subTest(raw=raw), patch.dict(
                    "os.environ",{"REPOPILOT_ISSUE_CONTEXT_CHARS":raw}):
                with self.assertRaisesRegex(ValueError,"[Ii]ssue context"):
                    configured_issue_context_chars()

    def test_agentic_cli_wires_requested_step_budget(self):
        observed=[]
        def mock_agent(repo,issue,model,url,token,max_steps=8,auto_issue_paths=False):
            observed.append((max_steps,auto_issue_paths))
            return self.proposed()
        with patch("repopilot.agentic_benchmark.propose_agentic_benchmark",mock_agent), \
             patch("repopilot.benchmark_attempt.attempt_one") as call:
            call.return_value={"status":"model_patch_proposed"}
            main(["sample__repo-123","--agentic","--max-steps","18"])
            kwargs=call.call_args.kwargs
            kwargs["model_proposer"](self.root,"issue","mock","http://127.0.0.1:11434/v1",None)
        self.assertEqual(observed,[(18,True)])

    def test_agentic_cli_rejects_unbounded_step_budget(self):
        with self.assertRaises(SystemExit):
            main(["sample__repo-123","--agentic","--max-steps","25"])

    def test_agentic_provenance_recorded_when_provided(self):
        def traced(*args):
            result,meta=self.proposed()
            return result,{**meta,"agent_steps":4,
                           "inspected_files":["main.py"],
                           "tool_trace":[{"step":1,"action":"read"}]}
        output=self.root/"traced"
        result=attempt_one(self.manifest,INSTANCE,output,
            dataset_loader=self.dataset,checkout=self.checkout,
            model_proposer=traced)
        self.assertEqual(result["agent_steps"],4)
        self.assertEqual(result["inspected_files"],["main.py"])
        self.assertEqual(result["tool_trace"][0]["action"],"read")

    def test_failed_model_attempt_is_not_a_success(self):
        output=self.root/"fail"
        result=attempt_one(self.manifest,INSTANCE,output,dataset_loader=self.dataset,
                           checkout=self.checkout,model_proposer=lambda *a:(_ for _ in ()).throw(ValueError("bad output")))
        self.assertEqual(result["status"],"failed_model_attempt")
        self.assertFalse((output/"unreviewed-prediction.json").exists())
    def test_reject_unknown_instance(self):
        with self.assertRaises(ValueError):
            attempt_one(self.manifest,"unknown__repo-1",self.root/"missing",dataset_loader=self.dataset)
    def test_refuse_overwriting_existing_evidence(self):
        out=self.root/"existing";out.mkdir()
        with self.assertRaises(ValueError):
            attempt_one(self.manifest,INSTANCE,out,dataset_loader=self.dataset)
if __name__=="__main__":unittest.main()
