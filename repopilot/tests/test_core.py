import json
import tempfile
import unittest
from pathlib import Path
from repopilot.context import index_python
from repopilot.spec import IssueSpec
from repopilot.patches import validate_patch,UnsafePatch
from repopilot.engine import execute,VerificationError
from repopilot.sandbox import RunResult
from repopilot.planner import propose,ProposalError

PATCH="diff --git a/calculator.py b/calculator.py\n--- a/calculator.py\n+++ b/calculator.py\n@@ -1,4 +1,4 @@\n def divide(a, b):\n     if b == 0:\n-        return 0  # BUG: should raise ZeroDivisionError\n+        raise ZeroDivisionError\n     return a / b\n"
TEST="import unittest\nfrom calculator import divide\nclass TestDivide(unittest.TestCase):\n def test_zero(self):\n  with self.assertRaises(ZeroDivisionError):divide(1,0)\n"
RAW={"issue_id":"demo","summary":"divide by zero","test_path":"tests/test_reproduction.py","reproduction_test":TEST,"patch":PATCH,"test_command":["python","-m","unittest","discover","-s","tests","-v"]}

class Tests(unittest.TestCase):
    def test_index(self):
        with tempfile.TemporaryDirectory() as t:
            Path(t,"a.py").write_text("class A:\n def foo(self):pass\n")
            found=index_python(Path(t))
            self.assertEqual([s.name for s in found],["A","A.foo"])
    def test_spec(self):
        self.assertEqual(IssueSpec.from_dict(RAW).issue_id,"demo")
    def test_bad_path(self):
        with self.assertRaises(ValueError):IssueSpec.from_dict({**RAW,"test_path":"../oops.py"})
    def test_bad_command(self):
        with self.assertRaises(ValueError):IssueSpec.from_dict({**RAW,"test_command":["sh","-c","echo bad"]})
    def test_patch(self):validate_patch(PATCH)
    def test_patch_traversal(self):
        with self.assertRaises(UnsafePatch):validate_patch(PATCH.replace("a/calculator.py","a/../calculator.py"))
    def test_patch_binary(self):
        with self.assertRaises(UnsafePatch):validate_patch(PATCH+"GIT binary patch\n")
    def test_propose_missing_model(self):
        with self.assertRaises(ProposalError):propose(Path("."),"bug","", "http://127.0.0.1:11434/v1")
    def test_propose_mock(self):
        with tempfile.TemporaryDirectory() as t:
            Path(t,"calculator.py").write_text("def divide(a, b):\n    if b == 0:\n        return 0  # BUG: should raise ZeroDivisionError\n    return a / b\n")
            obj={"choices":[{"message":{"content":json.dumps(RAW)}}],"usage":{"total_tokens":5}}
            spec,meta=propose(Path(t),"fix bug","local","http://127.0.0.1:11434/v1",client=lambda *_:obj)
            self.assertEqual(spec.summary,"divide by zero")
            self.assertEqual(meta["provider_reported_usage_by_attempt"][0]["total_tokens"],5)
    def test_lossless_nested_diff_is_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            Path(t,"calculator.py").write_text("def divide(a, b):\\n    if b == 0:\\n        return 0  # BUG: should raise ZeroDivisionError\\n    return a / b\\n".replace("\\n","\n"))
            body={**RAW,"patch":{"unified_diff":PATCH}}
            result={"choices":[{"message":{"content":json.dumps(body)}}]}
            spec,_=propose(Path(t),"fix divide bug","local","http://127.0.0.1:11434/v1",client=lambda *_:result)
            self.assertEqual(spec.patch,PATCH)
    def test_reject_arbitrary_patch_object(self):
        with tempfile.TemporaryDirectory() as t:
            Path(t,"calculator.py").write_text("def divide(a, b):\n    if b == 0:\n        return 0  # BUG: should raise ZeroDivisionError\n    return a / b\n")
            body={**RAW,"patch":{"files":[{"name":"calculator.py","code":"return 4"}]}}
            result={"choices":[{"message":{"content":json.dumps(body)}}]}
            with self.assertRaises(ProposalError):
                propose(Path(t),"fix divide bug","local","http://127.0.0.1:11434/v1",client=lambda *_:result)
    def test_model_structured_exact_edits_to_valid_patch(self):
        with tempfile.TemporaryDirectory() as t:
            Path(t,"calculator.py").write_text("def divide(a, b):\n    if b == 0:\n        return 0  # BUG: should raise ZeroDivisionError\n    return a / b\n")
            body={**RAW, "patch":{"edits":[{"path":"calculator.py",
                "old":"return 0  # BUG: should raise ZeroDivisionError",
                "new":"raise ZeroDivisionError"}]}}
            result={"choices":[{"message":{"content":json.dumps(body)}}]}
            spec,meta=propose(Path(t),"fix division by zero","local",
                "http://127.0.0.1:11434/v1",client=lambda *_:result)
            self.assertIn("diff --git a/calculator.py b/calculator.py",spec.patch)
            self.assertIn("+        raise ZeroDivisionError",spec.patch)
            self.assertEqual(meta["proposal_attempts"],1)

    def test_model_structured_edits_cannot_change_unindexed_file(self):
        with tempfile.TemporaryDirectory() as t:
            Path(t,"calculator.py").write_text("def divide(a,b):return 0\n")
            Path(t,"config.txt").write_text("API_TOKEN=abc\n")
            body={**RAW,"patch":{"edits":[{"path":"config.txt","old":"API_TOKEN","new":"EXPOSE"}]}}
            result={"choices":[{"message":{"content":json.dumps(body)}}]}
            with self.assertRaises(ProposalError):
                propose(Path(t),"fix bug","local","http://127.0.0.1:11434/v1",client=lambda *_:result)
    def test_verify_mock(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t,"repo");root.mkdir()
            (root/"calculator.py").write_text("def divide(a, b):\n    if b == 0:\n        return 0  # BUG: should raise ZeroDivisionError\n    return a / b\n")
            calls=[]
            def runner(work,command,timeout):
                calls.append(1)
                return RunResult(1 if len(calls)==2 else 0,4,"test")
            result=execute(root,IssueSpec.from_dict(RAW),Path(t,"result.json"),runner=runner)
            self.assertEqual(result["outcome"],"verified_in_sandbox")
            self.assertEqual(len(calls),3)
    def test_verify_rejects_false_repro(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t,"repo");root.mkdir()
            (root/"calculator.py").write_text("def divide(a, b):\n    if b == 0:\n        return 0  # BUG: should raise ZeroDivisionError\n    return a / b\n")
            with self.assertRaises(VerificationError):
                calls=[]
                def falsely_passing(work,command,timeout):
                    calls.append(1)
                    return RunResult(0,1,"passed")
                execute(root,IssueSpec.from_dict(RAW),Path(t,"r.json"),runner=falsely_passing)
    def test_verify_rejects_preexisting_failures(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t,"repo");root.mkdir()
            (root/"calculator.py").write_text("def divide(a, b):\n    if b == 0:\n        return 0  # BUG: should raise ZeroDivisionError\n    return a / b\n")
            with self.assertRaisesRegex(VerificationError,"Original test suite"):
                execute(root,IssueSpec.from_dict(RAW),Path(t,"r.json"),runner=lambda *a,**kw:RunResult(1,1,"unrelated failed"))
if __name__=="__main__":unittest.main()
