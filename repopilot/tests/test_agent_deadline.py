"""Regression coverage for deadline-aware provider calls.

These tests use simulated responses; they DO NOT assert SWE-bench resolution.
"""
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from repopilot.agentic_benchmark import (
    _provider, propose_agentic_benchmark, AgentToolError
)


class DeadlineAwareCallsTests(unittest.TestCase):
    def test_native_ollama_uses_remaining_deadline_cap(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return b'{"message":{"content":"{}"}}'
        class Opener:
            def __init__(self): self.timeouts=[]
            def open(self, request, *, timeout):
                self.timeouts.append(timeout)
                return Response()
        opener=Opener()
        with patch.dict("os.environ", {
            "REPOPILOT_OLLAMA_NATIVE": "1",
            "REPOPILOT_PROVIDER_TIMEOUT_SECONDS": "110"
        }), patch("repopilot.agentic_benchmark.urllib.request.build_opener",
                  return_value=opener):
            _provider("http://127.0.0.1:11434/v1", "coder", None, [],
                      request_timeout_seconds=3)
        self.assertEqual(len(opener.timeouts), 1)
        self.assertTrue(0 < opener.timeouts[0] <= 3)

    def test_openai_compatible_request_is_capped_by_agent_deadline(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size):
                return b'{"choices":[{"message":{"content":"{}"}}]}'
        class Opener:
            def __init__(self): self.timeouts=[]
            def open(self, request, *, timeout):
                self.timeouts.append(timeout)
                return Response()
        opener=Opener()
        with patch.dict("os.environ", {
            "REPOPILOT_OLLAMA_NATIVE": "",
            "REPOPILOT_PROVIDER_TIMEOUT_SECONDS": "110"
        }), patch("repopilot.agentic_benchmark.urllib.request.build_opener",
                  return_value=opener):
            _provider("https://example.org/v1", "coder", None, [],
                      request_timeout_seconds=5)
        self.assertEqual(len(opener.timeouts), 1)
        self.assertTrue(0 < opener.timeouts[0] <= 5)

    def test_retry_is_not_started_when_deadline_cannot_fit_backoff(self):
        class Opener:
            def __init__(self): self.calls=0
            def open(self, request, *, timeout):
                self.calls += 1
                raise urllib.error.HTTPError(
                    request.full_url, 503, "unavailable", None, None)
        opener=Opener()
        with patch.dict("os.environ", {"REPOPILOT_OLLAMA_NATIVE": ""}), \
             patch("repopilot.agentic_benchmark.urllib.request.build_opener",
                   return_value=opener), \
             patch("repopilot.agentic_benchmark.time.sleep",
                   side_effect=AssertionError("Do not retry")):
            with self.assertRaisesRegex(
                    AgentToolError, "deadline expired before retry"):
                _provider("https://example.org/v1", "coder", None, [],
                          request_timeout_seconds=1)
        self.assertEqual(opener.calls, 1)

    def test_invalid_remaining_budget_fails_before_network(self):
        with patch("repopilot.agentic_benchmark.urllib.request.build_opener",
                   side_effect=AssertionError("Network must not be contacted")):
            for value in (0, -1, 3601, "3"):
                with self.subTest(value=value), self.assertRaisesRegex(
                        AgentToolError, "remaining model request time budget"):
                    _provider("https://example.org/v1", "coder", None, [],
                              request_timeout_seconds=value)

    def test_agent_passes_remaining_time_to_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"pricing.py").write_text(
                "def subtotal(values):\n    return sum(values)\n")
            response={"choices":[{"message":{"content":json.dumps({
                "action":"finish", "edits":[{
                    "path":"pricing.py",
                    "old":"return sum(values)",
                    "new":"return round(sum(values), 2)"
                }]
            })}}]}
            with patch.dict("os.environ",
                            {"REPOPILOT_AGENT_BUDGET_SECONDS":"30"}), \
                 patch("repopilot.agentic_benchmark.time.monotonic",
                       side_effect=[0.0, 1.0, 2.0]), \
                 patch("repopilot.agentic_benchmark._provider",
                       return_value=response) as provider:
                patch_spec, meta=propose_agentic_benchmark(
                    root, "round the total", "coder",
                    "http://127.0.0.1:11434/v1",
                    max_steps=2, required_targets={"pricing.py"})
            self.assertIn("round(sum(values), 2)", patch_spec.patch)
            self.assertEqual(meta["agent_steps"], 1)
            self.assertEqual(
                provider.call_args.kwargs["request_timeout_seconds"], 26.0)


if __name__ == "__main__":
    unittest.main()
