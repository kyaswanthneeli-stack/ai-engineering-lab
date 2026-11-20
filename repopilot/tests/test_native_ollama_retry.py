"""Native Ollama network-recovery tests; no claims of benchmark resolution."""
import unittest
import urllib.error
from unittest.mock import patch

from repopilot.agentic_benchmark import (
    AgentToolError, TransientOllamaError, _local_ollama_chat, _provider
)

URL="http://127.0.0.1:11434/v1"


class NativeOllamaRecoveryTests(unittest.TestCase):
    def test_transient_timeout_retries_once_and_succeeds(self):
        response={"choices":[{"message":{"content":"{}"}}]}
        with patch.dict("os.environ", {"REPOPILOT_OLLAMA_NATIVE":"1",
                                      "REPOPILOT_PROVIDER_TIMEOUT_SECONDS":"110"}), \
             patch("repopilot.agentic_benchmark._local_ollama_chat",
                   side_effect=[TransientOllamaError("Local Ollama native chat failed or timed out"),
                                response]) as native, \
             patch("repopilot.agentic_benchmark.time.sleep") as sleep:
            result=_provider(URL,"coder",None,[],request_timeout_seconds=15)
        self.assertEqual(result,response)
        self.assertEqual(native.call_count,2)
        self.assertEqual(native.call_args_list[0].args[0],URL)
        self.assertEqual(native.call_args_list[1].args[0],URL)
        self.assertLessEqual(native.call_args_list[1].kwargs["request_timeout_seconds"],15)
        sleep.assert_called_once_with(2)

    def test_retry_budget_stops_after_second_transient_error(self):
        with patch.dict("os.environ",{"REPOPILOT_OLLAMA_NATIVE":"1"}), \
             patch("repopilot.agentic_benchmark._local_ollama_chat",
                   side_effect=TransientOllamaError("Local Ollama native chat failed or timed out")) as native, \
             patch("repopilot.agentic_benchmark.time.sleep") as sleep:
            with self.assertRaisesRegex(AgentToolError,"Local Ollama native chat failed"):
                _provider(URL,"coder",None,[])
        self.assertEqual(native.call_count,2)
        sleep.assert_called_once_with(2)

    def test_http_400_and_schema_errors_are_not_retried(self):
        for reason in ("Local Ollama native API HTTP 400",
                       "Local Ollama native response was invalid JSON"):
            with self.subTest(reason=reason), \
                 patch.dict("os.environ",{"REPOPILOT_OLLAMA_NATIVE":"1"}), \
                 patch("repopilot.agentic_benchmark._local_ollama_chat",
                       side_effect=AgentToolError(reason)) as native, \
                 patch("repopilot.agentic_benchmark.time.sleep") as sleep:
                with self.assertRaisesRegex(AgentToolError,reason):
                    _provider(URL,"coder",None,[])
                native.assert_called_once()
                sleep.assert_not_called()

    def test_deadline_prohibits_native_retry_after_timeout(self):
        with patch.dict("os.environ",{"REPOPILOT_OLLAMA_NATIVE":"1"}), \
             patch("repopilot.agentic_benchmark.time.monotonic",
                   side_effect=[0.0,0.0,4.0]), \
             patch("repopilot.agentic_benchmark._local_ollama_chat",
                   side_effect=TransientOllamaError("Local Ollama native chat failed or timed out")) as native, \
             patch("repopilot.agentic_benchmark.time.sleep") as sleep:
            with self.assertRaisesRegex(AgentToolError,"deadline expired before native retry"):
                _provider(URL,"coder",None,[],request_timeout_seconds=1)
        native.assert_called_once()
        sleep.assert_not_called()

    def test_http_503_transient_but_400_permanent(self):
        class Opener:
            def __init__(self,status): self.status=status
            def open(self,request,*,timeout):
                raise urllib.error.HTTPError(request.full_url,self.status,"error",None,None)
        for status,expected in ((503,TransientOllamaError),(400,AgentToolError)):
            with self.subTest(status=status), \
                 patch("repopilot.agentic_benchmark.urllib.request.build_opener",
                       return_value=Opener(status)):
                with self.assertRaises(expected) as context:
                    _local_ollama_chat(URL,"coder",[],256,request_timeout_seconds=5)
                self.assertIn(str(status),str(context.exception))
                if status==400:
                    self.assertNotIsInstance(context.exception,TransientOllamaError)


if __name__=="__main__":
    unittest.main()
