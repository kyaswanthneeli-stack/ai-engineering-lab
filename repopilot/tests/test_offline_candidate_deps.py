"""Prove the optional offline smoke runtime cannot be selected by model input.

Unit mocks validate command construction; the CI workflow additionally builds
the trusted image and runs a real networkless baseline-pass/candidate-fail case.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repopilot.candidate_smoke import (
    _approved_image, _run_docker, smoke_candidate
)

PATCH = ("diff --git a/math_fixture.py b/math_fixture.py\n"
         "--- a/math_fixture.py\n+++ b/math_fixture.py\n"
         "@@ -1,2 +1,2 @@\n"
         " from mpmath import mp\n"
         "-def value(): return mp.sqrt(9)\n"
         "+def value(): raise ValueError('regression')\n")


class OfflineDependencyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/"math_fixture.py").write_text(
            "from mpmath import mp\ndef value(): return mp.sqrt(9)\n")
        self.issue = ("Preserve existing behavior\n"
                      "```python\nfrom math_fixture import value\n"
                      "assert int(value()) == 3\n```")

    def test_default_image_remains_small_offline_python(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(_approved_image(), "python:3.12-alpine")

    def test_only_exact_trusted_image_is_accepted(self):
        with patch.dict("os.environ", {
            "REPOPILOT_CANDIDATE_SMOKE_IMAGE": "repopilot-candidate-deps:py310"
        }):
            self.assertEqual(_approved_image(), "repopilot-candidate-deps:py310")
        for tag in ("docker.io/library/python:latest", "busybox:latest",
                    "repopilot-candidate-deps:latest", "img;echo command"):
            with self.subTest(tag=tag), patch.dict("os.environ", {
                "REPOPILOT_CANDIDATE_SMOKE_IMAGE": tag
            }):
                self.assertIsNone(_approved_image())
                with patch("repopilot.candidate_smoke.shutil.which",
                           return_value="/usr/bin/docker") as which:
                    result = smoke_candidate(self.root, PATCH, self.issue)
                self.assertEqual(result["status"], "skipped")
                self.assertEqual(result["reason"], "unapproved_runtime_image")
                which.assert_not_called()

    def test_trusted_image_still_has_no_network_or_privileges(self):
        seen = []
        def run(args, **kwargs):
            seen.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")
        with patch.dict("os.environ", {
            "REPOPILOT_CANDIDATE_SMOKE_IMAGE": "repopilot-candidate-deps:py310"
        }), patch("repopilot.candidate_smoke.subprocess.run", side_effect=run):
            code, unsafe = _run_docker(
                self.root, "import mpmath", overlay=None,
                targets=["math_fixture.py"], timeout=4)
        self.assertEqual((code, unsafe), (0, False))
        argv = seen[0]
        self.assertIn("--pull=never", argv)
        self.assertIn("--network=none", argv)
        self.assertIn("--read-only", argv)
        self.assertIn("--cap-drop=ALL", argv)
        self.assertIn("--security-opt=no-new-privileges", argv)
        self.assertIn("--memory=512m", argv)
        self.assertIn("--cpus=1", argv)
        self.assertIn("--pids-limit=64", argv)
        self.assertIn("repopilot-candidate-deps:py310", argv)

    def test_dependency_dockerfile_contains_only_dev_owned_pins(self):
        dockerfile = (Path(__file__).resolve().parents[1] /
                      "ci/Dockerfile.candidate-smoke").read_text()
        for allowed in ("python:3.10-slim-bookworm",
                        "mpmath==1.3.0", "numpy==1.23.5",
                        "scipy==1.10.1", "asgiref==3.7.2",
                        "--only-binary=:all:"):
            self.assertIn(allowed, dockerfile)
        for forbidden in ("pip install -r", "setup.py install",
                          "pip install -e", "COPY .", "ADD ."):
            self.assertNotIn(forbidden, dockerfile)


if __name__ == "__main__":
    unittest.main()
