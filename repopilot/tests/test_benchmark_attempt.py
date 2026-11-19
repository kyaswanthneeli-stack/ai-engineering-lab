import json
import tempfile
import unittest
from pathlib import Path
from repopilot.benchmark_attempt import attempt_one

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
