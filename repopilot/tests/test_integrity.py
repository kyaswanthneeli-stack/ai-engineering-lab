import unittest
from repopilot.integrity import proposal_digest
from repopilot.spec import IssueSpec


RAW = {
    "issue_id": "owner/repo#1", "summary": "demo",
    "test_path": "tests/test_reproduction.py",
    "reproduction_test": "import unittest\nclass TestBug(unittest.TestCase):\n def test_bug(self):\n  self.assertEqual(1,2)\n",
    "patch": "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-x=1\n+x=2\n",
    "test_command": ["python","-m","unittest","discover","-s","tests","-v"]
}


class IntegrityTests(unittest.TestCase):
    def test_deterministic_digest(self):
        spec=IssueSpec.from_dict(RAW)
        self.assertEqual(proposal_digest(spec),proposal_digest(spec))
        self.assertEqual(len(proposal_digest(spec)),64)
    def test_patch_mismatch_changes_digest(self):
        first=IssueSpec.from_dict(RAW)
        modified=IssueSpec.from_dict({**RAW,"patch":RAW["patch"].replace("+x=2","+x=3")})
        self.assertNotEqual(proposal_digest(first),proposal_digest(modified))
    def test_test_mismatch_changes_digest(self):
        first=IssueSpec.from_dict(RAW)
        modified=IssueSpec.from_dict({**RAW,"reproduction_test":RAW["reproduction_test"]+"# comment\n"})
        self.assertNotEqual(proposal_digest(first),proposal_digest(modified))
if __name__=="__main__":
    unittest.main()
