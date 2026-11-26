import json
import base64
import tempfile
import unittest
from pathlib import Path
from repopilot.pipeline import run_issue
from repopilot.engine import execute
from repopilot.sandbox import RunResult
from repopilot.spec import IssueSpec
from repopilot.pr import publish_approved_draft,PublishError,patch_targets,GitHubPathNotFound
from repopilot.integrity import proposal_digest

PATCH="diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
SPEC=IssueSpec.from_dict({"issue_id":"issue-2","summary":"demo","test_path":"tests/test_reproduction.py","reproduction_test":"import unittest\nclass TestBug(unittest.TestCase):\n def test_bug(self):\n  self.assertEqual(1,1)\n","patch":PATCH,"test_command":["python","-m","unittest","discover","-s","tests","-v"]})

class PipelineTests(unittest.TestCase):
    def test_pipeline_success_with_mock_model_and_verifier(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/"run"
            result=run_issue(Path(d),"https://github.com/a/b/issues/2",folder,
                issue_reader=lambda _:{"issue_id":"a/b#2","text":"fix","url":"https://github.com/a/b/issues/2"},
                model_proposer=lambda *a:(SPEC,{"model":"mock","status":"unverified_proposal","provider_reported_usage":{"total_tokens":11}}),
                verifier=lambda *a:{"issue_id":"issue-2","outcome":"verified_in_sandbox","before":{"exit_code":1},"after":{"exit_code":0},"draft_pr_created":False})
            self.assertEqual(result["outcome"],"verified_in_sandbox")
            self.assertTrue((folder/"dashboard.html").is_file())
            self.assertTrue((folder/"proposal.json").is_file())
            self.assertTrue(result["model_generated_proposal"])
            self.assertEqual(result["model_metadata"]["model"],"mock")
    def test_pipeline_captures_error_not_fake_success(self):
        with tempfile.TemporaryDirectory() as d:
            result=run_issue(Path(d),"https://github.com/a/b/issues/2",Path(d)/"run",
                issue_reader=lambda _:{"issue_id":"a/b#2","text":"fix"},
                model_proposer=lambda *a: (_ for _ in ()).throw(RuntimeError("no provider")))
            self.assertEqual(result["outcome"],"failed")
            self.assertFalse(result["model_generated_proposal"])
    def test_pipeline_renders_recorded_baseline_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"repo"
            root.mkdir()
            folder=Path(d)/"run"

            def verifier(repo, spec, output):
                return execute(repo,spec,output,runner=lambda *args,**kwargs:RunResult(
                    124,30,"Timed out; Docker reported forced container removal",True))

            report=run_issue(root,"https://github.com/a/b/issues/2",folder,
                issue_reader=lambda _:{"issue_id":"a/b#2","text":"fix"},
                model_proposer=lambda *a:(SPEC,{"model":"fixture"}),
                verifier=verifier)
            self.assertEqual(report["failed_stage"],"baseline_tests")
            self.assertTrue(report["baseline"]["timed_out"])
            self.assertEqual(report["model_metadata"]["model"],"fixture")
            dashboard=(folder/"dashboard.html").read_text()
            self.assertIn("Docker reported forced container removal",dashboard)
            self.assertIn("UNVERIFIED / FAILED",dashboard)

    def test_draft_pr_needs_approval(self):
        with self.assertRaises(PublishError):
            publish_approved_draft(Path("."),SPEC,{"outcome":"verified_in_sandbox","issue_id":"issue-2","before":{"exit_code":1},"after":{"exit_code":0}},"a/b","NO")
    def test_draft_pr_rejects_unverified(self):
        with self.assertRaises(PublishError):
            publish_approved_draft(Path("."),SPEC,{"outcome":"failed","issue_id":"issue-2"},"a/b","I_APPROVE_DRAFT_PR")
    def test_mock_draft_pr_created_in_reviewed_subdirectory(self):
        class FakeApi:
            test_exists = False
            def __init__(self):
                self.calls=[]
            def call(self,method,path,data=None):
                self.calls.append((method,path,data))
                if (method,path)==("GET",""):
                    return {"full_name":"a/b","default_branch":"main"}
                if path=="/git/ref/heads/main":
                    return {"object":{"sha":"012345abcdef"}}
                if (method,path)==("GET","/contents/nested/a.py?ref=012345abcdef"):
                    return {"type":"file","encoding":"base64","content":base64.b64encode(b"x = 1\n").decode(),"sha":"blob1"}
                if (method,path)==("GET","/contents/nested/tests/test_reproduction.py?ref=012345abcdef"):
                    if self.test_exists:
                        return {"type":"file"}
                    raise GitHubPathNotFound("Missing test")
                if method=="GET" and path=="/git/commits/012345abcdef":
                    return {"tree":{"sha":"basetree"}}
                if method=="POST" and path=="/git/trees":
                    assert data["base_tree"]=="basetree"
                    return {"sha":"newtree"}
                if method=="POST" and path=="/git/commits":
                    assert data["tree"]=="newtree"
                    assert data["parents"]==["012345abcdef"]
                    return {"sha":"single_commit"}
                if method=="POST" and path=="/git/refs":
                    assert data["sha"]=="single_commit"
                    return {"ref":data["ref"]}
                if method=="POST" and path=="/pulls":
                    assert data["draft"] is True
                    return {"html_url":"https://github.com/a/b/pull/2","number":2}
                raise AssertionError((method,path))
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)
            (src/"a.py").write_text("x = 1\n")
            spec=IssueSpec.from_dict({**{k:getattr(SPEC,k) for k in ("issue_id","summary","test_path","reproduction_test","patch")},
                                     "issue_id":"a/b#2","test_command":list(SPEC.test_command)})
            verified={"outcome":"verified_in_sandbox","issue_id":"a/b#2",
                "baseline":{"exit_code":0,"output":"Ran 1 test in 0.001s\n\nOK\n","timed_out":False},
                "before":{"exit_code":1,"output":"FAIL: test_bug\nRan 2 tests in 0.001s\n","timed_out":False},
                "after":{"exit_code":0,"output":"Ran 2 tests in 0.001s\n\nOK\n","timed_out":False},
                "proposal_sha256":proposal_digest(spec)}
            api=FakeApi()
            result=publish_approved_draft(src,spec,verified,"a/b","I_APPROVE_DRAFT_PR",api=api,repo_subdir="nested")
            self.assertEqual(result["url"],"https://github.com/a/b/pull/2")
            self.assertEqual(result["commit_sha"],"single_commit")
            self.assertFalse(any(method=="PUT" for method,_,_ in api.calls))
            trees=[data for method,path,data in api.calls if method=="POST" and path=="/git/trees"]
            self.assertEqual(len(trees),1)
            self.assertEqual({item["path"] for item in trees[0]["tree"]},
                             {"nested/a.py","nested/tests/test_reproduction.py"})
            api=FakeApi()
            api.test_exists=True
            with self.assertRaisesRegex(PublishError,"already exists in the remote base"):
                publish_approved_draft(src,spec,verified,"a/b","I_APPROVE_DRAFT_PR",api=api,repo_subdir="nested")
            self.assertFalse(any(method=="POST" for method,_,_ in api.calls))

            api=FakeApi()
            verified["before"]["timed_out"]=True
            with self.assertRaisesRegex(PublishError,"evidence required"):
                publish_approved_draft(src,spec,verified,"a/b","I_APPROVE_DRAFT_PR",api=api,repo_subdir="nested")
            self.assertEqual(api.calls,[])

    def test_draft_pr_rejects_changed_patch_after_verification(self):
        real_spec=IssueSpec.from_dict({
            "issue_id":"a/b#2","summary":"test","test_path":"tests/test_reproduction.py",
            "reproduction_test":SPEC.reproduction_test,"patch":PATCH,
            "test_command":list(SPEC.test_command)})
        verified={"issue_id":"a/b#2","outcome":"verified_in_sandbox",
                  "baseline":{"exit_code":0},"before":{"exit_code":1},
                  "after":{"exit_code":0},"proposal_sha256":proposal_digest(real_spec)}
        altered=IssueSpec.from_dict({
            "issue_id":"a/b#2","summary":"test","test_path":"tests/test_reproduction.py",
            "reproduction_test":SPEC.reproduction_test+"# changed after verification\\n",
            "patch":PATCH,"test_command":list(SPEC.test_command)})
        with self.assertRaisesRegex(PublishError,"does not match"):
            publish_approved_draft(Path("."),altered,verified,"a/b","I_APPROVE_DRAFT_PR")
    def test_patch_targets(self):
        self.assertEqual(patch_targets(PATCH),["a.py"])
if __name__=="__main__":unittest.main()
