import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from repopilot.checkout import pinned_checkout,CheckoutError

SHA="a"*40
URL="https://github.com/example/project/issues/12"
class CheckoutTests(unittest.TestCase):
    def test_rejects_invalid_revision(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(CheckoutError):
                pinned_checkout(URL,"main",Path(d)/"work")
    def test_rejects_non_github_issue(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(CheckoutError):
                pinned_checkout("https://other.example/issues/1",SHA,Path(d)/"work")
    def test_commands_never_invoke_shell_or_submodules(self):
        seen=[]
        def fake(args,**kwargs):
            seen.append((args,kwargs))
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as d:
            pinned_checkout(URL,SHA,Path(d)/"work",run=fake)
        self.assertEqual(len(seen),4)
        self.assertEqual(seen[-1][0][-1],SHA)
        self.assertTrue(all(not kw.get("shell",False) for _,kw in seen))
        self.assertFalse(any("submodule" in str(cmd) for cmd,_ in seen))
        self.assertTrue(all(kw["env"]["GIT_TERMINAL_PROMPT"]=="0" for _,kw in seen))
    def test_existing_destination_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(CheckoutError):
                pinned_checkout(URL,SHA,Path(d))
if __name__=="__main__":
    unittest.main()
