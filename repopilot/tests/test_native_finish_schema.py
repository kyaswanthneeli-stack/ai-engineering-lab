import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from repopilot.agentic_benchmark import propose_agentic_benchmark, _local_ollama_chat


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

    def test_opt_in_native_nonthinking_does_not_change_default_requests(self):
        payloads = []

        def respond(request, *, timeout):
            payloads.append(json.loads(request.data))
            return BytesIO(b'{"message":{"content":"{}"}}')

        with patch("repopilot.agentic_benchmark.urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect = respond
            with patch.dict(os.environ, {"REPOPILOT_OLLAMA_DISABLE_THINKING": ""}):
                _local_ollama_chat("http://localhost:11434/v1", "fixture", [], 256)
            with patch.dict(os.environ, {"REPOPILOT_OLLAMA_DISABLE_THINKING": "1"}):
                _local_ollama_chat("http://localhost:11434/v1", "fixture", [], 256)
        self.assertNotIn("think", payloads[0])
        self.assertIs(payloads[1]["think"], False)


    def test_unassisted_compact_final_constrains_inspected_paths_and_budget(self):
        calls = []
        action = {"action": "finish", "edits": [
            {"path": "pricing.py", "old": "return cents",
             "new": "return cents / 100"}]}
        def provider(url, model, token, messages, **kwargs):
            calls.append(kwargs)
            return {"choices": [{"message": {"content": json.dumps(action)}}]}
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {
            "REPOPILOT_OLLAMA_NATIVE": "1", "REPOPILOT_CANDIDATE_SMOKE": "0",
            "REPOPILOT_CONFIRM_RANKED_SOURCE": "1", "REPOPILOT_COMPACT_DISCOVERY": "1",
            "REPOPILOT_COMPACT_FINAL": "1",
        }), patch("repopilot.agentic_benchmark._provider", side_effect=provider):
            root = Path(temp)
            (root / "pricing.py").write_text("def dollars(cents):\n    return cents\n")
            proposal, meta = propose_agentic_benchmark(
                root, "Pricing dollars conversion returns cents",
                "fixture", "http://localhost:11434/v1",
                max_steps=4, auto_issue_paths=True)
        self.assertEqual([call.get("token_cap") for call in calls], [256, 256, 512])
        self.assertEqual(calls[-1]["finish_paths"], ("pricing.py",))
        self.assertNotIn("old_choices", calls[-1])
        self.assertIn("return cents / 100", proposal.patch)
        self.assertIn("final_phase_started", [event["action"] for event in meta["tool_trace"]])


    def test_exact_edit_retry_preserves_schema_and_rejects_invented_source(self):
        from repopilot.agentic_benchmark import AgentToolError
        calls = []
        def provider(url, model, token, messages, **kwargs):
            calls.append((list(messages), dict(kwargs)))
            old = "return imaginary" if len(calls)==1 else "return cents"
            action = {"action":"finish","edits":[
                {"path":"pricing.py","old":old,"new":"return cents / 100"}]}
            return {"choices":[{"message":{"content":json.dumps(action)}}]}
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {
            "REPOPILOT_OLLAMA_NATIVE":"1",
            "REPOPILOT_CANDIDATE_SMOKE":"0",
        }), patch("repopilot.agentic_benchmark._provider",side_effect=provider):
            root=Path(temp)
            (root/"pricing.py").write_text("def dollars(cents):\n    return cents\n")
            proposal, meta=propose_agentic_benchmark(
                root,"Return dollars","fixture","http://localhost:11434/v1",
                required_targets={"pricing.py"},max_steps=3,native_exact_edits=True)
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[1][1]["finish_paths"],("pricing.py",))
        feedback=calls[1][0][-1]["content"]
        self.assertIn("edits only, not files or patch",feedback)
        self.assertNotIn("return imaginary",feedback)
        self.assertIn("return cents / 100",proposal.patch)
        self.assertIn("finish_rejected",[x["action"] for x in meta["tool_trace"]])
