import json
import tempfile
import unittest
from pathlib import Path
from repopilot.repair_loop import run_with_repair
from repopilot.spec import IssueSpec

PATCH="diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
def spec():
    return IssueSpec.from_dict({
        "issue_id":"agent","summary":"patch","test_path":"tests/test_reproduction.py",
        "reproduction_test":"import unittest\nclass TestBug(unittest.TestCase):\n def test_bug(self):\n  self.assertTrue(True)\n",
        "patch":PATCH,"test_command":["python","-m","unittest","discover","-s","tests","-v"]})
def issue(_):
    return {"issue_id":"example/repo#1","url":"https://github.com/example/repo/issues/1","text":"Fix a.py"}

class RepairTests(unittest.TestCase):
    def good_verifier(self,repo,spec,path):
        return {"issue_id":spec.issue_id,"outcome":"verified_in_sandbox",
                "baseline":{"exit_code":0},"before":{"exit_code":1},
                "after":{"exit_code":0},"elapsed_ms":5}
    def test_retry_after_failed_verification(self):
        with tempfile.TemporaryDirectory() as td:
            calls=[]
            def verifier(repo,spec,path):
                calls.append(1)
                if len(calls)==1:
                    raise RuntimeError("failing tests")
                return self.good_verifier(repo,spec,path)
            prompts=[]
            def model(repo,prompt,*args):
                prompts.append(prompt)
                return spec(),{"model":"mock-model"}
            report=run_with_repair(Path(td),"https://github.com/example/repo/issues/1",
                Path(td)/"run",issue_reader=issue,model_proposer=model,verifier=verifier)
            self.assertEqual(report["outcome"],"verified_in_sandbox")
            self.assertEqual(report["successful_attempt"],2)
            self.assertEqual(len(prompts),2)
            self.assertIn("PREVIOUS ATTEMPT FAILED",prompts[1])
            self.assertTrue((Path(td)/"run"/"dashboard.html").exists())
            self.assertTrue((Path(td)/"run"/"attempt-01-proposal.json").exists())
            self.assertTrue((Path(td)/"run"/"attempt-02-proposal.json").exists())
    def test_docker_failure_feedback_reaches_retry_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            prompts=[]
            def model(repo,prompt,*args):
                prompts.append(prompt)
                return spec(),{"model":"mock"}
            calls=[]
            def verifier(repo,proposal,path):
                calls.append(1)
                if len(calls)==1:
                    path.write_text(json.dumps({
                        "outcome":"failed","failed_stage":"patched_tests",
                        "after":{"exit_code":1,"output":"FAIL: test_rounding expected 0.33"}
                    }))
                    raise RuntimeError("patch failed")
                return self.good_verifier(repo,proposal,path)
            report=run_with_repair(Path(td),"https://github.com/example/repo/issues/1",
                Path(td)/"attempt",issue_reader=issue,model_proposer=model,verifier=verifier)
            self.assertEqual(report["successful_attempt"],2)
            self.assertIn("test_rounding",prompts[1])
            self.assertTrue(report["attempts"][0]["has_test_failure_evidence"])

    def test_all_attempts_fail_without_claiming_success(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"run"
            report=run_with_repair(Path(td),"https://github.com/example/repo/issues/1",out,
                max_attempts=2,issue_reader=issue,
                model_proposer=lambda *a:(spec(),{"model":"mock"}),
                verifier=lambda *a:(_ for _ in ()).throw(RuntimeError("failed")))
            self.assertEqual(report["outcome"],"failed")
            self.assertEqual(len(report["attempts"]),2)
            self.assertNotIn("successful_attempt",report)
    def test_invalid_attempt_count(self):
        with self.assertRaises(ValueError):
            run_with_repair(Path("."),"x",Path("x"),max_attempts=4)
    def test_setup_failure_records_no_fake_run(self):
        with tempfile.TemporaryDirectory() as td:
            report=run_with_repair(Path(td),"x",Path(td)/"run",
                issue_reader=lambda *a:(_ for _ in ()).throw(ValueError("missing")))
            self.assertEqual(report["outcome"],"failed")
            self.assertEqual(report["attempts"],[])
if __name__=="__main__":
    unittest.main()
