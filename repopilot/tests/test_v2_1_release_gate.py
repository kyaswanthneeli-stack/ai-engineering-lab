"""Guard the post-v2.0.0 immutable release workflow."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "repopilot"


class V21ReleaseGatesTests(unittest.TestCase):
    def test_release_is_main_only_and_refuses_republish(self):
        workflow = (ROOT / ".github/workflows/repopilot-v2-1-release.yml").read_text()
        for required in (
                "workflow_dispatch:",
                "branches:\n      - main",
                ".github/workflows/repopilot-v2-1-release.yml",
                "refs/heads/main",
                "contents: write",
                "gh release view v2.1.0",
                "git ls-remote --tags",
                "gh release create v2.1.0",
                '--target "$GITHUB_SHA"',
                "RELEASE_NOTES_v2.1.0.md"):
            with self.subTest(required=required):
                self.assertIn(required, workflow)

    def test_checks_cover_integrity_docker_doctor_and_installable_wheel(self):
        workflow = (ROOT / ".github/workflows/repopilot-v2-1-release.yml").read_text()
        for required in (
                "repopilot.swebench_results",
                "official-score-2026-11-20.json",
                "official-predictions-2026-11-20.jsonl",
                "coverage run",
                "doctor > .runs/release-v2.1-doctor-offline.json",
                "docker pull python:3.12-alpine",
                "python -m build --sdist --wheel",
                "repopilot-2.1.0-*.whl",
                "python -m venv .runs/repopilot-wheel-smoke",
                "--no-index --no-deps",
                "sha256sum dist/*"):
            with self.subTest(required=required):
                self.assertIn(required, workflow)
        self.assertTrue((PROJECT / "RELEASE_NOTES_v2.1.0.md").is_file())

    def test_historical_v2_release_gate_remains_immutable(self):
        old = (ROOT / ".github/workflows/repopilot-v2-release.yml").read_text()
        self.assertIn("gh release create v2.0.0", old)
        self.assertNotIn("gh release create v2.1.0", old)


if __name__ == "__main__":
    unittest.main()
