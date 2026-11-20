"""Protect the immutable v2.1.1 deadline-reliability patch release."""
import unittest
from pathlib import Path
import tomllib
from importlib.metadata import version
from repopilot import __version__


ROOT=Path(__file__).resolve().parents[2]


class PatchReleaseGateTests(unittest.TestCase):
    def test_version_matches_runtime_and_distribution(self):
        pyproject=tomllib.loads((ROOT/"repopilot/pyproject.toml").read_text())
        self.assertEqual(pyproject["project"]["version"], "2.1.1")
        self.assertEqual(__version__, "2.1.1")
        self.assertEqual(version("repopilot"), "2.1.1")

    def test_release_gated_on_evidence_tests_and_clean_wheel(self):
        workflow=(ROOT/".github/workflows/repopilot-v2-1-1-release.yml").read_text()
        for required in (
                "branches:\n      - main",
                "refs/heads/main",
                "contents: write",
                "gh release view v2.1.1",
                "git ls-remote --tags",
                "official-score-2026-11-20.json",
                "official-predictions-2026-11-20.jsonl",
                "coverage run",
                "docker pull python:3.12-alpine",
                "doctor > .runs/release-v2.1-doctor-offline.json",
                "python -m build --sdist --wheel",
                "repopilot-2.1.1-*.whl",
                "python -m venv .runs/repopilot-wheel-smoke",
                "--no-index --no-deps",
                "gh release create v2.1.1",
                "RELEASE_NOTES_v2.1.1.md"):
            with self.subTest(required=required):
                self.assertIn(required, workflow)
        self.assertTrue((ROOT/"repopilot/RELEASE_NOTES_v2.1.1.md").is_file())

    def test_v2_1_0_tag_protection_workflow_is_unchanged(self):
        old=(ROOT/".github/workflows/repopilot-v2-1-release.yml").read_text()
        self.assertIn("gh release create v2.1.0", old)
        self.assertNotIn("gh release create v2.1.1", old)


if __name__=="__main__":
    unittest.main()
