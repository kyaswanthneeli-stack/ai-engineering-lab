"""Prevent shipping a CLI image before test gates or on untrusted PRs."""
import unittest
from pathlib import Path


class RcDeploymentWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flow=(Path(__file__).resolve().parents[2] /
                  ".github/workflows/repopilot-cli-container.yml"
                 ).read_text(encoding="utf-8")

    def test_distribution_requires_real_python_docker_and_image_gates(self):
        flow=self.flow
        for token in (
            "python -m coverage run --source=repopilot -m unittest discover -s tests -v",
            "python -m repopilot.cli verify",
            "SANDBOX FAIL-BEFORE/PASS-AFTER: VERIFIED",
            "OFFLINE CANDIDATE REGRESSION CHECK: VERIFIED",
            "docker build --pull -f container/Dockerfile.cli",
            "docker run --rm --read-only --network none --cap-drop ALL",
            "--security-opt no-new-privileges",
            "--user 65532:65532",
            "NONROOT OFFLINE OCI CLI INDEX: VERIFIED",
            "python -m build --sdist --wheel",
            "--no-index --no-deps",
            "sha256sum dist/",
            "repopilot-v2.2.0rc1-release-candidate",
        ):
            with self.subTest(token=token):
                self.assertIn(token,flow)

    def test_publish_only_on_protected_main_after_tests(self):
        flow=self.flow
        for token in (
            "branches:",
            "      - main",
            "github.event_name != 'pull_request' && github.ref == 'refs/heads/main'",
            "packages: write",
            "contents: write",
            "docker/login-action@v3",
            "ghcr.io/kyaswanthneeli-stack/repopilot:sha-",
            "Refusing overwrite.",
            "gh release create v2.2.0rc1",
            "--prerelease",
            "secrets.GITHUB_TOKEN",
        ):
            with self.subTest(token=token):
                self.assertIn(token,flow)
        self.assertNotIn("docker.sock",flow)
        self.assertNotIn("docker push repopilot-cli:rc",flow)
        self.assertNotIn("repopilot:latest",flow)
        self.assertLess(flow.index("Run full Python suite"),flow.index("Build and smoke-test nonroot"))
        self.assertLess(flow.index("Build and smoke-test nonroot"),
                        flow.index("Publish commit-scoped GHCR"))

    def test_security_policy_rejects_unattended_host_service(self):
        root=Path(__file__).resolve().parents[1]
        security=(root/"SECURITY.md").read_text()
        deployment=(root/"docs/DEPLOYMENT.md").read_text()
        self.assertIn("Never mount",deployment)
        self.assertIn("Human",security)
        self.assertIn("1/12",security)
        self.assertNotIn("EXPOSE 8000",self.flow)


if __name__ == "__main__":
    unittest.main()
