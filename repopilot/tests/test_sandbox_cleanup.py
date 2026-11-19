import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from repopilot.sandbox import run_tests

COMMAND=("python","-m","unittest","discover","-s","tests","-v")

class SandboxCleanupTests(unittest.TestCase):
    def test_failed_cleanup_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as temp:
            def run(args, **kwargs):
                if args[:2]==["docker","run"]:
                    raise subprocess.TimeoutExpired(args, 1)
                if args[:3]==["docker","rm","-f"]:
                    return subprocess.CompletedProcess(args, 1, b"", b"failed")
                raise AssertionError(args)
            with patch("repopilot.sandbox.shutil.which", return_value="/usr/bin/docker"):
                with patch("repopilot.sandbox.subprocess.run", side_effect=run):
                    result=run_tests(Path(temp),COMMAND,timeout=1)
            self.assertTrue(result.timed_out)
            self.assertEqual(result.exit_code,124)
            self.assertIn("discard worker",result.output)

    def test_successful_cleanup_is_differentiated(self):
        with tempfile.TemporaryDirectory() as temp:
            def run(args, **kwargs):
                if args[:2]==["docker","run"]:
                    raise subprocess.TimeoutExpired(args, 1)
                return subprocess.CompletedProcess(args, 0, b"", b"")
            with patch("repopilot.sandbox.shutil.which", return_value="/usr/bin/docker"):
                with patch("repopilot.sandbox.subprocess.run", side_effect=run):
                    result=run_tests(Path(temp),COMMAND,timeout=1)
            self.assertIn("reported forced container removal",result.output)
            self.assertTrue(result.timed_out)
if __name__=="__main__":
    unittest.main()
