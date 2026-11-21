"""Prepublication gate checks for the separate stable v2.2.0 release workflow."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT.parent / ".github/workflows/repopilot-v2-2-stable-release.yml"


class StableReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_stable_release_is_manual_main_only_and_immutable(self):
        flow = self.text
        self.assertIn("  workflow_dispatch:", flow)
        self.assertNotIn("\n  push:", flow)
        self.assertNotIn("\n  pull_request:", flow)
        self.assertIn("github.ref == 'refs/heads/main'", flow)
        self.assertIn("github.event_name == 'workflow_dispatch'", flow)
        self.assertIn("Refusing overwrite.", flow)
        self.assertIn("gh release create v2.2.0", flow)
        self.assertNotIn("gh release create v2.2.0rc1", flow)
        self.assertNotIn("--prerelease", flow)
        self.assertIn("Release notes are still a draft", flow)
        self.assertIn("assert p['project']['version']=='2.2.0'", flow)
        self.assertNotIn("repopilot:latest", flow)

    def test_stable_pr_preflight_has_no_publish_privileges(self):
        flow = (ROOT.parent /
                ".github/workflows/repopilot-v2-2-stable-preflight.yml"
               ).read_text(encoding="utf-8")
        self.assertIn("  pull_request:", flow)
        self.assertIn("permissions:\n  contents: read", flow)
        self.assertIn("persist-credentials: false", flow)
        self.assertIn("repo.full_name == github.repository", flow)
        self.assertIn("repopilot-2.2.0-*.whl", flow)
        self.assertIn("--read-only --network none --cap-drop ALL", flow)
        self.assertIn("test -f dist/repopilot-2.2.0.tar.gz", flow)
        self.assertIn("sha256sum dist/*", flow)
        self.assertNotIn("packages: write", flow)
        self.assertNotIn("contents: write", flow)
        self.assertNotIn("gh release create", flow)
        self.assertNotIn("docker push", flow)
        self.assertNotIn("secrets.GITHUB_TOKEN", flow)

    def test_release_requires_version_test_and_sandbox_gates(self):
        flow = self.text
        for expected in (
            "assert p['project']['version']=='2.2.0'",
            "assert repopilot.__version__=='2.2.0'",
            "python -m coverage run --source=repopilot -m unittest discover -s tests -v",
            "SANDBOX FAIL-BEFORE/PASS-AFTER: VERIFIED",
            "OFFLINE CANDIDATE REGRESSION CHECK: VERIFIED",
            "Build versioned wheel and source archive",
            "Verify clean offline wheel installation",
            "--read-only --network none --cap-drop ALL",
            "--user 65532:65532",
            "NONROOT OFFLINE OCI CLI INDEX: VERIFIED",
            "ghcr.io/kyaswanthneeli-stack/repopilot:sha-",
            "packages: write",
            "contents: write",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, flow)
        self.assertLess(flow.index("Compile and run full Python suite"),
                        flow.index("Build and smoke-test nonroot networkless OCI"))
        self.assertLess(flow.index("Build and smoke-test nonroot networkless OCI"),
                        flow.index("Publish commit-scoped GHCR CLI image"))
        self.assertLess(flow.index("Publish commit-scoped GHCR CLI image"),
                        flow.index("Publish immutable stable GitHub Release"))


if __name__ == "__main__":
    unittest.main()
