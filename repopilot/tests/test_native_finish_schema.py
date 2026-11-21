import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from repopilot.agentic_benchmark import propose_agentic_benchmark


class NativeFinishTests(unittest.TestCase):
    def test_final_request_constrains_edits_to_the_inspected_file(self):
        formats = []
        def respond(request, *, timeout):
            formats.append(json.loads(request.data)["format"])
            action = {"action": "finish", "edits": [
                {"path": "prices.py", "old": "return cents", "new": "return cents / 100"}]}
            return BytesIO(json.dumps({"message": {"content": json.dumps(action)}}).encode())
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {
            "REPOPILOT_OLLAMA_NATIVE": "1", "REPOPILOT_CANDIDATE_SMOKE": "0"
        }), patch("repopilot.agentic_benchmark.urllib.request.build_opener") as opener:
            root = Path(temp)
            (root / "prices.py").write_text("def dollars(cents):\n    return cents\n")
            opener.return_value.open.side_effect = respond
            for enabled in (False, True):
                proposal, _ = propose_agentic_benchmark(root, "Return dollars", "fixture",
                    "http://localhost:11434/v1", required_targets={"prices.py"}, max_steps=2,
                    native_exact_edits=enabled, exact_edit_anchors=("return cents",) if enabled else ())
                self.assertIn("return cents / 100", proposal.patch)
        self.assertEqual(formats[0], "json")
        edits = formats[1]["properties"]["edits"]["items"]
        self.assertEqual(edits["properties"]["path"]["enum"], ["prices.py"])
        self.assertEqual(edits["properties"]["old"]["enum"], ["return cents"])
        self.assertEqual(edits["required"], ["path", "old", "new"])

    def test_longer_retry_budget_uses_exact_edits_on_first_model_call(self):
        calls = []
        action = {"action": "finish", "edits": [
            {"path": "prices.py", "old": "return cents",
             "new": "return cents / 100"}]}

        def provider(url, model, token, messages, **kwargs):
            calls.append(kwargs)
            return {"choices": [{"message": {"content": json.dumps(action)}}]}

        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {
            "REPOPILOT_OLLAMA_NATIVE": "1", "REPOPILOT_CANDIDATE_SMOKE": "0",
        }), patch("repopilot.agentic_benchmark._provider", side_effect=provider):
            root = Path(temp)
            (root / "prices.py").write_text(
                "def dollars(cents):\\n    return cents\\n".replace("\\n", "\n")
            )
            proposal, _ = propose_agentic_benchmark(
                root, "Return dollars", "fixture", "http://localhost:11434/v1",
                required_targets={"prices.py"}, max_steps=4,
                native_exact_edits=True, exact_edit_anchors=("return cents",)
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["finish_paths"], ("prices.py",))
        self.assertEqual(calls[0]["old_choices"], ("return cents",))
        self.assertIn("return cents / 100", proposal.patch)
