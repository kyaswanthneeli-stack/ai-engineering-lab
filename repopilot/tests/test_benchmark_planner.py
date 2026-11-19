import json
import tempfile
import unittest
from pathlib import Path
from repopilot.benchmark_planner import propose_benchmark,BenchmarkProposalError


class BenchmarkPlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)
        (self.repo/"invoice.py").write_text("def total(items):\n    return sum(items)\n")

    def client(self,content):
        return lambda *_:{"choices":[{"message":{"content":json.dumps(content)}}],"usage":{"total_tokens":44}}

    def test_exact_edits_produce_unverified_patch(self):
        patch,meta=propose_benchmark(self.repo,"invoice total bug","coder",
            "http://127.0.0.1:11434/v1",client=self.client({"edits":[{
                "path":"invoice.py","old":"return sum(items)","new":"return round(sum(items),2)"}]}))
        self.assertIn("round(sum(items),2)",patch.patch)
        self.assertEqual(meta["provider_reported_usage_by_attempt"][0]["total_tokens"],44)
        self.assertIs(meta["officially_evaluated"],False)

    def test_reject_unindexed_file(self):
        with self.assertRaises(BenchmarkProposalError):
            propose_benchmark(self.repo,"invoice total bug","coder",
                "http://127.0.0.1:11434/v1",client=self.client({"edits":[{
                    "path":"other.py","old":"foo","new":"bar"}]}))

    def test_no_test_module_required(self):
        patch,meta=propose_benchmark(self.repo,"total bug","coder",
            "http://127.0.0.1:11434/v1",client=self.client({"edits":[{
                "path":"invoice.py","old":"return sum(items)","new":"return sum(items) + 1"}]}))
        self.assertNotIn("test_command",meta)
        self.assertTrue(patch.patch.startswith("diff --git"))

    def test_reject_non_https_remote(self):
        with self.assertRaises(BenchmarkProposalError):
            propose_benchmark(self.repo,"bug","coder","http://example.org/v1",
                client=self.client({"edits":[]}))


if __name__=="__main__":
    unittest.main()
