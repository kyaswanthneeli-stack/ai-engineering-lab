import unittest
from repopilot.review import review_proposal
from repopilot.spec import IssueSpec

PATCH="diff --git a/mod.py b/mod.py\n--- a/mod.py\n+++ b/mod.py\n@@ -1 +1 @@\n-x=1\n+x=2\n"
BASE={"issue_id":"issue","summary":"fix",
      "test_path":"tests/test_reproduction.py",
      "reproduction_test":"import unittest\nclass TestBug(unittest.TestCase):\n def test_bug(self):\n  self.assertEqual(1,1)\n",
      "patch":PATCH,
      "test_command":["python","-m","unittest","discover","-s","tests","-v"]}
class ReviewTests(unittest.TestCase):
    def spec(self,**changes):
        return IssueSpec.from_dict({**BASE,**changes})
    def test_review_required_for_normal_patch(self):
        result=review_proposal(self.spec())
        self.assertEqual(result["status"],"review_required")
        self.assertEqual(result["blockers"],0)
    def test_block_invalid_syntax(self):
        self.assertEqual(review_proposal(self.spec(reproduction_test="def !!!!"))["status"],"blocked")
    def test_block_test_without_assertion_method(self):
        result=review_proposal(self.spec(reproduction_test="def helper():\n pass\n"))
        self.assertEqual(result["status"],"blocked")
    def test_block_test_importing_subprocess(self):
        test="import subprocess\nclass X:\n def test_bad(self):\n  pass\n"
        result=review_proposal(self.spec(reproduction_test=test))
        self.assertTrue(any(f["code"]=="dangerous_test_import" for f in result["findings"]))
    def test_warning_for_added_shell(self):
        patch=PATCH.replace("+x=2","+x=os.system('date')")
        self.assertEqual(review_proposal(self.spec(patch=patch))["warnings"],1)
    def test_block_embedded_secret(self):
        patch=PATCH.replace("+x=2","+api_key = 'ABCDEFGHIJKL'")
        self.assertEqual(review_proposal(self.spec(patch=patch))["status"],"blocked")
if __name__=="__main__":
    unittest.main()
