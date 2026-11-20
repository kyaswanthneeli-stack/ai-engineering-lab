"""Protect semantic version and formal v2.0.0 release safeguards."""
from importlib.metadata import version
from pathlib import Path
import tomllib
import unittest

from repopilot import __version__


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = REPO_ROOT / "repopilot"


class V2ReleaseGateTests(unittest.TestCase):
    def test_distribution_and_runtime_have_same_release_version(self):
        metadata=tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
        self.assertEqual(metadata["project"]["version"], "2.1.1")
        self.assertEqual(__version__, "2.1.1")
        self.assertEqual(version("repopilot"), "2.1.1")

    def test_publish_only_from_main_after_release_checks(self):
        workflow=(REPO_ROOT / ".github/workflows/repopilot-v2-release.yml").read_text()
        for required in (
                "branches:\n      - main",
                "contents: write",
                "refs/heads/main",
                "repopilot.swebench_results",
                "official-score-2026-11-20.json",
                "official-predictions-2026-11-20.jsonl",
                "test_published_official_evidence_nov20",
                "coverage run",
                "docker pull python:3.12-alpine",
                "python -m build",
                "gh release create v2.0.0",
                "--target \"$GITHUB_SHA\"",
                "gh release view v2.0.0",
                "git ls-remote --tags",
                "RELEASE_NOTES_v2.0.0.md"):
            with self.subTest(required=required):
                if required == "test_published_official_evidence_nov20":
                    self.assertTrue((PROJECT_ROOT / "tests/test_published_official_evidence_nov20.py").is_file())
                else:
                    self.assertIn(required, workflow)


if __name__ == "__main__":
    unittest.main()
