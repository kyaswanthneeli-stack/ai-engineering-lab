"""Preflight tests prevent accidental or unsupported benchmark claims."""
import json
import tempfile
import unittest
from pathlib import Path
from repopilot.swebench_export import export_predictions, load_manifest


def manifest():
    return {"tasks": [
        {"instance_id": f"example__repo-{i}", "repo": "example/repo", "base_commit": "a" * 40, "status": "not_attempted"}
        for i in range(10)
    ]}


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = self.root / "manifest.json"
        self.submissions = self.root / "submissions"
        self.submissions.mkdir()
        self.output = self.root / "predictions.jsonl"
        self.manifest.write_text(json.dumps(manifest()), encoding="utf-8")

    def test_unattempted_is_never_reported_as_solved(self):
        result = export_predictions(self.manifest, self.submissions, self.output)
        self.assertEqual(result["selected_tasks"], 10)
        self.assertEqual(result["submitted_predictions"], 0)
        self.assertIsNone(result["official_resolution_rate"])
        self.assertEqual(self.output.read_text(), "")

    def test_real_submission_exports_official_fields_only(self):
        submitted = {
            "instance_id": "example__repo-0", "base_commit": "a" * 40,
            "model_name_or_path": "local-coder-3b", "generated_by_model": True,
            "human_reviewed": True, "model_patch": "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n"
        }
        (self.submissions / "example__repo-0.json").write_text(json.dumps(submitted))
        result = export_predictions(self.manifest, self.submissions, self.output)
        self.assertEqual(result["submitted_predictions"], 1)
        self.assertIsNone(result["official_resolution_rate"])
        prediction = json.loads(self.output.read_text().splitlines()[0])
        self.assertEqual(set(prediction), {"instance_id", "model_name_or_path", "model_patch"})

    def test_rejects_unreviewed_candidate(self):
        submitted = {
            "instance_id": "example__repo-0", "base_commit": "a" * 40,
            "model_name_or_path": "local", "generated_by_model": True,
            "human_reviewed": False, "model_patch": "diff --git a/a.py b/a.py\n"
        }
        (self.submissions / "example__repo-0.json").write_text(json.dumps(submitted))
        with self.assertRaises(ValueError):
            export_predictions(self.manifest, self.submissions, self.output)

    def test_rejects_wrong_commit(self):
        submitted = {
            "instance_id": "example__repo-0", "base_commit": "b" * 40,
            "model_name_or_path": "local", "generated_by_model": True,
            "human_reviewed": True, "model_patch": "diff --git a/a.py b/a.py\n"
        }
        (self.submissions / "example__repo-0.json").write_text(json.dumps(submitted))
        with self.assertRaises(ValueError):
            export_predictions(self.manifest, self.submissions, self.output)

    def test_rejects_duplicate_manifest_ids(self):
        data = manifest()
        data["tasks"][1]["instance_id"] = data["tasks"][0]["instance_id"]
        self.manifest.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            load_manifest(self.manifest)

    def test_rejects_too_few_tasks(self):
        self.manifest.write_text(json.dumps({"tasks": manifest()["tasks"][:9]}))
        with self.assertRaises(ValueError):
            load_manifest(self.manifest)


if __name__ == "__main__":
    unittest.main()
