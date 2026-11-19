import unittest
import tempfile
from pathlib import Path
from repopilot.swebench import select_instances,write_manifest

class SwebenchSelectionTests(unittest.TestCase):
    def sample_loader(self,*args):
        return [{"instance_id":f"repo__example-{i}","repo":"repo/example","base_commit":"a"*40} for i in range(20)]
    def test_deterministic_selection(self):
        a=select_instances(12,73,loader=self.sample_loader)
        b=select_instances(12,73,loader=self.sample_loader)
        self.assertEqual(a,b)
        self.assertEqual(len(set(x["instance_id"] for x in a)),12)
        self.assertTrue(all(x["status"]=="not_attempted" for x in a))
    def test_reject_invalid_limit(self):
        with self.assertRaises(ValueError):
            select_instances(31,loader=self.sample_loader)
    def test_manifest_does_not_claim_solved(self):
        with tempfile.TemporaryDirectory() as d:
            r=write_manifest(Path(d)/"manifest.json",12,loader=self.sample_loader)
            self.assertEqual(r["status"],"selected_not_evaluated")
            self.assertTrue(all(x["model_result"] is None for x in r["tasks"]))
if __name__=="__main__":unittest.main()
