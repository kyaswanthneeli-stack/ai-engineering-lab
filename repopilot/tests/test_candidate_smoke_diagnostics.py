"""Failure categories must stay useful without persisting untrusted stderr."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from repopilot.candidate_smoke import _failure_category, _run_docker, smoke_candidate


class SmokeDiagnosticTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "value.py").write_text("value = 1\n")
        self.proposal = ("diff --git a/value.py b/value.py\n"
                         "--- a/value.py\n+++ b/value.py\n"
                         "@@ -1 +1 @@\n-value = 1\n+value = 2\n")

    def test_fixed_categories_discard_module_names_paths_and_credentials(self):
        for message, category in [
            ("ModuleNotFoundError: PRIVATE_MODULE API_KEY=secret", "import_error"),
            ("ImportError: /private/path", "import_error"),
            ("django.core.exceptions.ImproperlyConfigured: PRIVATE_CONFIG", "configuration_error"),
            ("SyntaxError: PRIVATE_SOURCE", "syntax_error"),
            ("AssertionError: PRIVATE_ASSERT", "assertion_failed"),
            ("PermissionError: /private/secret", "permission_error"),
            ("FileNotFoundError: PRIVATE_FILENAME", "file_not_found"),
            ("unknown untrusted arbitrary text", "nonzero_exit"),
        ]:
            with self.subTest(message=message):
                self.assertEqual(_failure_category(1, message), category)
        self.assertEqual(_failure_category(125, "ModuleNotFoundError: secret"),
                         "container_runtime_error")
        self.assertIsNone(_failure_category(0, "ModuleNotFoundError: spoof"))

    def run_with(self, outcomes, issue="Fix value"):
        outcomes = iter(outcomes)
        real_run = subprocess.run
        def run(args, **kwargs):
            if args[0] != "docker":
                return real_run(args, **kwargs)
            if args[1] == "rm":
                return subprocess.CompletedProcess(args, 0)
            code, stderr = next(outcomes)
            kwargs["stderr"].write(stderr.encode())
            return subprocess.CompletedProcess(args, code)
        with patch("repopilot.candidate_smoke.shutil.which", return_value="docker"), patch(
                "repopilot.candidate_smoke.subprocess.run", side_effect=run):
            return smoke_candidate(self.root, self.proposal, issue)

    def test_import_error_baseline_stays_inconclusive_with_sanitized_evidence(self):
        result = self.run_with([(1, "ModuleNotFoundError: SECRET_MODULE token=SECRET")])
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["baseline_exit_code"], 1)
        self.assertEqual(result["baseline_failure_category"], "import_error")
        self.assertNotIn("SECRET", json.dumps(result))

    def test_fallback_records_separate_original_and_fallback_failures(self):
        issue = "```python\nimport value\nassert value.value == 99\n```"
        result = self.run_with([(1, "AssertionError: PRIVATE_ASSERT"),
                                (1, "ImportError: PRIVATE_MODULE")], issue)
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["baseline_failure_category"], "assertion_failed")
        self.assertEqual(result["fallback_baseline_failure_category"], "import_error")
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_candidate_runtime_error_never_becomes_code_regression(self):
        for code, category in [(125, "container_runtime_error"),
                               (137, "resource_or_signal_exit")]:
            with self.subTest(code=code):
                result = self.run_with([(0, ""), (code, "daemon error token=SECRET")])
                self.assertEqual(result["status"], "inconclusive")
                self.assertEqual(result["reason"], "candidate_or_cleanup_unavailable")
                self.assertEqual(result["candidate_failure_category"], category)
                self.assertNotIn("SECRET", json.dumps(result))

    def test_real_nonzero_candidate_after_passing_baseline_is_still_regression(self):
        result = self.run_with([(0, ""), (1, "AssertionError: PRIVATE")])
        self.assertEqual(result["status"], "regression")
        self.assertEqual(result["candidate_failure_category"], "assertion_failed")

    def test_timeout_cleanup_uncertainty_remains_inconclusive(self):
        def run(args, **kwargs):
            if args[1] == "run":
                raise subprocess.TimeoutExpired(args, 1)
            return subprocess.CompletedProcess(args, 1)
        evidence = {}
        with patch("repopilot.candidate_smoke.subprocess.run", side_effect=run):
            code, unsafe = _run_docker(self.root, "import value", overlay=None,
                targets=["value.py"], timeout=1, diagnostics=evidence)
        self.assertIsNone(code)
        self.assertTrue(unsafe)
        self.assertEqual(evidence["baseline_failure_category"], "probe_timeout")
