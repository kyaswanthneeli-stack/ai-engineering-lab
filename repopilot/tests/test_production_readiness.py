"""Security and distribution contract for the supervised RepoPilot CLI."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repopilot.github_issue import _NoRedirect, IssueFetchError, fetch_public_issue
from repopilot.pipeline import run_issue
import repopilot

ROOT = Path(__file__).resolve().parents[1]


class ProductionReadinessTests(unittest.TestCase):
    def test_error_body_is_not_persisted_in_json_or_html(self):
        private = "Bearer token-super-secret-123456789"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "runs"
            result = run_issue(
                Path(td), "https://github.com/acme/demo/issues/1", out,
                issue_reader=lambda _: {
                    "issue_id": "acme/demo#1", "text": "Public test issue",
                    "url": "https://github.com/acme/demo/issues/1",
                },
                model_proposer=lambda *args: (_ for _ in ()).throw(
                    RuntimeError(private)),
            )
            self.assertEqual(result["outcome"], "failed")
            self.assertEqual(result["error_type"], "RuntimeError")
            self.assertNotIn(private, json.dumps(result))
            for name in ("run.json", "dashboard.html"):
                self.assertNotIn(private, (out / name).read_text(encoding="utf-8"))
            self.assertFalse(result["draft_pr_created"])

    def test_issue_api_does_not_follow_redirects(self):
        with self.assertRaisesRegex(IssueFetchError, "redirects are prohibited"):
            _NoRedirect().redirect_request(
                None, None, 302, "Found", {}, "http://127.0.0.1/steal")

    def test_issue_retrieval_uses_bounded_nonredirecting_client(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size):
                self_size = 150_001
                if size != self_size:
                    raise AssertionError("Unbounded read")
                return json.dumps({"title": "Test", "body": "A public report"}).encode()
        class Client:
            def open(self, request, timeout):
                self.request = request
                self.timeout = timeout
                return Response()
        client = Client()
        with patch("repopilot.github_issue.urllib.request.build_opener",
                   return_value=client) as opener:
            result = fetch_public_issue("https://github.com/acme/demo/issues/3")
        self.assertEqual(result["issue_id"], "acme/demo#3")
        self.assertEqual(client.timeout, 12)
        self.assertEqual(
            client.request.full_url,
            "https://api.github.com/repos/acme/demo/issues/3")
        self.assertIsInstance(opener.call_args.args[0], _NoRedirect)

    def test_package_version_matches_source(self):
        import tomllib
        import repopilot
        config = tomllib.loads((ROOT / "pyproject.toml").read_text())
        from importlib.metadata import version
        self.assertEqual(config["project"]["version"], repopilot.__version__)
        self.assertEqual(version("repopilot"), repopilot.__version__)

    def test_container_contract_no_root_or_public_server(self):
        dockerfile = (ROOT / "container/Dockerfile.cli").read_text()
        for expected in (
            "USER 65532:65532",
            'ENTRYPOINT ["python", "-m", "repopilot.cli"]',
            "COPY src/ ./src/",
            "PIP_DISABLE_PIP_VERSION_CHECK=1",
            f"repopilot=={repopilot.__version__}",
        ):
            self.assertIn(expected, dockerfile)
        for forbidden in (
            "EXPOSE ", "COPY . .", "ADD http", "RUN curl",
            "RUN wget", "apt-get install docker", "GITHUB_TOKEN=",
        ):
            self.assertNotIn(forbidden, dockerfile)
        ignore = (ROOT / ".dockerignore").read_text()
        self.assertIn(".git", ignore)
        self.assertIn(".runs", ignore)
        self.assertIn("tests", ignore)

    def test_deployment_runbooks_are_present_and_truthful(self):
        for path in (
            "docs/DEPLOYMENT.md", "docs/OPERATIONS.md",
            "SECURITY.md", "RELEASE_NOTES_v2.2.0rc1.md", ".env.example",
        ):
            self.assertTrue((ROOT / path).is_file(), path)
        deploy = (ROOT / "docs/DEPLOYMENT.md").read_text()
        self.assertIn("Never mount", deploy)
        self.assertIn("1/12", deploy)
        self.assertIn("doctor --live", deploy)
        self.assertNotIn("production SaaS is live", deploy)

if __name__ == "__main__":
    unittest.main()
