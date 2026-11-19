import json
import base64
import tempfile
import unittest
from pathlib import Path
from repopilot.pipeline import run_issue
from repopilot.spec import IssueSpec
from repopilot.pr import publish_approved_draft,PublishError,patch_targets

PATCH="diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
SPEC=IssueSpec.from_dict({"issue_id":"issue-2","summary":"demo","test_path":"tests/test_reproduction.py","reproduction_test":"import unittest\n","patch":PATCH,"test_command":["python","-m","unittest","discover","-s","tests","-v"]})

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
    def test_draft_pr_needs_approval(self):
        with self.assertRaises(PublishError):
            publish_approved_draft(Path("."),SPEC,{"outcome":"verified_in_sandbox","issue_id":"issue-2","before":{"exit_code":1},"after":{"exit_code":0}},"a/b","NO")
    def test_draft_pr_rejects_unverified(self):
        with self.assertRaises(PublishError):
            publish_approved_draft(Path("."),SPEC,{"outcome":"failed","issue_id":"issue-2"},"a/b","I_APPROVE_DRAFT_PR")
    def test_mock_draft_pr_created_in_reviewed_subdirectory(self):
        class FakeApi:
            def __init__(self):
                self.calls=[]
            def call(self,method,path,data=None):
                self.calls.append((method,path,data))
                if (method,path)==("GET",""):
                    return {"full_name":"a/b","default_branch":"main"}
                if path=="/git/ref/heads/main":
                    return {"object":{"sha":"012345abcdef"}}
                if method=="GET" and "/contents/nested/a.py" in path:
                    return {"type":"file","encoding":"base64","content":base64.b64encode(b"x = 1\\n").decode(),"sha":"blob1"}
                if method=="POST" and path=="/pulls":
                    assert data["draft"] is True
                    return {"html_url":"https://github.com/a/b/pull/2","number":2}
                return {}
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)
            (src/"a.py").write_text("x = 1\\n")
            spec=IssueSpec.from_dict({**{k:getattr(SPEC,k) for k in ("issue_id","summary","test_path","reproduction_test","patch")},
                                     "issue_id":"a/b#2","test_command":list(SPEC.test_command)})
            verified={"outcome":"verified_in_sandbox","issue_id":"a/b#2","baseline":{"exit_code":0},
                "before":{"exit_code":1},"after":{"exit_code":0}}
            api=FakeApi()
            result=publish_approved_draft(src,spec,verified,"a/b","I_APPROVE_DRAFT_PR",api=api,repo_subdir="nested")
            self.assertEqual(result["url"],"https://github.com/a/b/pull/2")
            paths=[p for method,p,_ in api.calls if method=="PUT"]
            self.assertIn("/contents/nested/a.py",paths)
            self.assertIn("/contents/nested/tests/test_reproduction.py",paths)
    def test_patch_targets(self):
        self.assertEqual(patch_targets(PATCH),["a.py"])
if __name__=="__main__":unittest.main()
