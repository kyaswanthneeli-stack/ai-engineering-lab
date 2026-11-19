import json
import tempfile
import unittest
from pathlib import Path
from repopilot.github_issue import fetch_public_issue,IssueFetchError
from repopilot.dashboard import render_dashboard
from repopilot.benchmark import aggregate

class ReportingTests(unittest.TestCase):
    def test_issue_parsed_with_mock_transport(self):
        result=fetch_public_issue("https://github.com/example/project/issues/12",transport=lambda req:json.dumps({"title":"Handle a zero value","body":"Fix division"}).encode())
        self.assertEqual(result["issue_id"],"example/project#12")
        self.assertIn("Fix division",result["text"])
    def test_issue_rejects_non_github_host(self):
        with self.assertRaises(IssueFetchError):
            fetch_public_issue("https://github.com.evil.test/org/repo/issues/1")
    def test_issue_rejects_pr(self):
        with self.assertRaises(IssueFetchError):
            fetch_public_issue("https://github.com/example/project/issues/12",transport=lambda req:json.dumps({"title":"PR","body":"text","pull_request":{}}).encode())
    def test_dashboard_escapes_script(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"review.html"
            render_dashboard({"outcome":"failed","note":"<script>alert(1)</script>"},path)
            content=path.read_text()
            self.assertNotIn("<script>alert(1)</script>",content)
            self.assertIn("&lt;script&gt;",content)
    def test_dashboard_verified_logic(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"run.html"
            render_dashboard({"outcome":"verified_in_sandbox","before":{"exit_code":1},"after":{"exit_code":0}},p)
            self.assertIn("VERIFIED: fail before",p.read_text())
    def test_benchmark_distinguishes_fixture(self):
        result=aggregate([{"outcome":"verified_in_sandbox","before":{"exit_code":1},"after":{"exit_code":0},"elapsed_ms":1000},{"outcome":"error","model_generated_proposal":True,"elapsed_ms":2000}],"test fixture")
        self.assertEqual(result["verified_patches"],1)
        self.assertEqual(result["model_generated_attempts"],1)
        self.assertEqual(result["model_generated_verified"],0)
        self.assertEqual(result["model_success_rate"],0)
    def test_benchmark_empty(self):
        result=aggregate([])
        self.assertIsNone(result["model_success_rate"])
        self.assertEqual(result["attempts"],0)
if __name__=="__main__":
    unittest.main()
