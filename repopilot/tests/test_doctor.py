import contextlib
import io
import json
import subprocess
import unittest
from unittest.mock import patch

from repopilot.cli import main
from repopilot.doctor import inspect_runtime


class LocalDoctorTests(unittest.TestCase):
    def _tools(self):
        return patch("repopilot.doctor.shutil.which",
                     side_effect=lambda name: "/fake/" + name)

    def _docker(self):
        return patch(
            "repopilot.doctor.subprocess.run",
            return_value=subprocess.CompletedProcess(
                ["docker"], 0, stdout="27.0", stderr=""))

    def test_default_mode_never_runs_subprocess_or_http(self):
        with self._tools(), \
             patch("repopilot.doctor.subprocess.run",
                   side_effect=AssertionError("subprocess attempted")), \
             patch("repopilot.doctor.urllib.request.build_opener",
                   side_effect=AssertionError("HTTP attempted")):
            report = inspect_runtime(
                model="qwen2.5-coder:3b",
                base_url="http://127.0.0.1:11434/v1")
        self.assertFalse(report["ready_for_verified_workflow"])
        self.assertEqual(report["mode"], "offline")
        statuses = {x["name"]: x["status"] for x in report["checks"]}
        self.assertEqual(statuses["docker_daemon"], "not_checked")
        self.assertEqual(statuses["model_available"], "not_checked")

    def test_live_local_ollama_check_is_bounded_and_read_only(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, limit):
                if limit != 200_001:
                    raise AssertionError("Unbounded model inventory")
                return json.dumps(
                    {"models": [{"name": "qwen2.5-coder:3b"}]}
                ).encode()
        class Opener:
            def __init__(self):
                self.urls = []
            def open(self, request, timeout):
                self.urls.append((request.full_url, request.get_method(), timeout))
                return Response()
        opener = Opener()
        with self._tools(), self._docker(), \
             patch("repopilot.doctor.urllib.request.build_opener",
                   return_value=opener):
            report = inspect_runtime(
                live=True, model="qwen2.5-coder:3b",
                base_url="http://127.0.0.1:11434/v1")
        self.assertTrue(report["ready_for_verified_workflow"])
        self.assertEqual(opener.urls, [
            ("http://127.0.0.1:11434/api/tags", "GET", 4)])
        self.assertNotIn("http://127.0.0.1", json.dumps(report))

    def test_live_missing_model_fails_readiness_not_fabricate_success(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, n):
                return b'{"models":[{"name":"different-model"}]}'
        class Opener:
            def open(self, request, timeout):
                return Response()
        with self._tools(), self._docker(), \
             patch("repopilot.doctor.urllib.request.build_opener",
                   return_value=Opener()):
            report = inspect_runtime(
                live=True, model="qwen2.5-coder:3b",
                base_url="http://localhost:11434/v1")
        self.assertFalse(report["ready_for_verified_workflow"])
        self.assertEqual({x["name"]: x["status"] for x in report["checks"]}
                         ["model_available"], "fail")

    def test_external_https_never_probed_and_not_claimed_ready(self):
        with self._tools(), self._docker(), \
             patch("repopilot.doctor.urllib.request.build_opener",
                   side_effect=AssertionError("Never contact remote hosts")):
            report = inspect_runtime(
                live=True, model="confidential-model",
                base_url="https://example.org/v1")
        status = {x["name"]: x["status"] for x in report["checks"]}
        self.assertEqual(status["provider_config"], "pass")
        self.assertEqual(status["model_available"], "not_checked")
        self.assertFalse(report["ready_for_verified_workflow"])
        self.assertNotIn("example.org", json.dumps(report))

    def test_invalid_remote_http_and_credentials_are_not_accepted(self):
        for url in (
            "http://example.org/v1",
            "https://secret:password@example.org/v1",
            "https://example.org/v1?api_key=secret"):
            with self.subTest(url=url), \
                 self._tools(), \
                 patch("repopilot.doctor.urllib.request.build_opener",
                       side_effect=AssertionError("No remote requests")):
                report = inspect_runtime(
                    model="sample", base_url=url)
            status = {x["name"]: x["status"] for x in report["checks"]}
            self.assertEqual(status["provider_config"], "fail")
            self.assertFalse(report["ready_for_verified_workflow"])
            self.assertNotIn("secret", json.dumps(report))

    def test_docker_missing_is_reported_without_invoking_daemon(self):
        with patch("repopilot.doctor.shutil.which",
                   side_effect=lambda name: None if name == "docker"
                   else "/fake/git"), \
             patch("repopilot.doctor.subprocess.run",
                   side_effect=AssertionError("Unexpected docker command")):
            report = inspect_runtime(
                live=True, model="sample",
                base_url="https://example.org/v1")
        status = {x["name"]: x["status"] for x in report["checks"]}
        self.assertEqual(status["docker_cli"], "fail")
        self.assertEqual(status["docker_daemon"], "fail")

    def test_cli_offline_json_and_live_exit_code(self):
        offline = {
            "mode": "offline", "checks": [], "ready_for_verified_workflow": False}
        out = io.StringIO()
        with patch("repopilot.doctor.inspect_runtime", return_value=offline) as inspected, \
             contextlib.redirect_stdout(out):
            main(["doctor"])
        self.assertEqual(json.loads(out.getvalue())["mode"], "offline")
        inspected.assert_called_once_with(live=False)
        with patch("repopilot.doctor.inspect_runtime",
                   return_value={**offline, "mode": "live"}), \
             contextlib.redirect_stdout(io.StringIO()), \
             self.assertRaises(SystemExit) as raised:
            main(["doctor", "--live"])
        self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
