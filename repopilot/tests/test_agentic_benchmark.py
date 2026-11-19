import json
import tempfile
import unittest
import urllib.error
from unittest.mock import patch
from pathlib import Path
from repopilot.agentic_benchmark import propose_agentic_benchmark,AgentToolError,_provider


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)
        (self.repo/"pricing.py").write_text("def subtotal(values):\n    return sum(values)\n")
        (self.repo/"checkout.py").write_text("from pricing import subtotal\ndef total(values):\n    return subtotal(values)\n")
    def sequence(self,steps):
        it=iter(steps)
        def client(*args):
            return {"choices":[{"message":{"content":json.dumps(next(it))}}],"usage":{"total_tokens":5}}
        return client

    def test_opt_in_local_native_ollama_skips_compatible_api(self):
        with patch.dict("os.environ",{"REPOPILOT_OLLAMA_NATIVE":"1",
                                      "REPOPILOT_MAX_TOKENS":"512"}), patch(
              "repopilot.agentic_benchmark._local_ollama_chat",
              return_value={"choices":[{"message":{"content":"{}"}}]}) as native:
            response=_provider("http://127.0.0.1:11434/v1","mock",None,[])
        native.assert_called_once_with(
            "http://127.0.0.1:11434/v1","mock",[],512)
        self.assertEqual(response["choices"][0]["message"]["content"],"{}")

    def test_opt_in_native_never_sends_remote_source_or_token(self):
        with patch.dict("os.environ",{"REPOPILOT_OLLAMA_NATIVE":"1"}):
            with self.assertRaisesRegex(AgentToolError,"restricted to local Ollama"):
                _provider("https://example.com/v1","mock",None,[])
            with self.assertRaisesRegex(AgentToolError,"does not use API tokens"):
                _provider("http://127.0.0.1:11434/v1","mock","test-secret",[])

    def test_model_fenced_json_is_parsed_as_action(self):
        messages=[]
        def client(url,model,token,history):
            messages.append(list(history))
            return {"choices":[{"message":{"content":
                "```json\\n"+json.dumps({"action":"finish","edits":[{
                    "path":"pricing.py","old":"return sum(values)",
                    "new":"return round(sum(values),2)"}]})+"\\n```"}}]}
        patch,meta=propose_agentic_benchmark(
            self.repo,"fix rounding","mock","http://127.0.0.1:11434/v1",
            client=client,max_steps=3,required_targets={"pricing.py"})
        self.assertIn("round(sum(values),2)",patch.patch)

    def test_invalid_model_json_retries_without_reusing_malformed_text(self):
        contents=["not-json","{invalid","",json.dumps({"action":"finish",
                  "edits":[{"path":"pricing.py","old":"return sum(values)",
                            "new":"return round(sum(values),2)"}]})]
        inputs=[]
        def client(url,model,token,history):
            inputs.append(list(history))
            return {"choices":[{"message":{"content":contents.pop(0)}}]}
        patch,meta=propose_agentic_benchmark(
            self.repo,"fix rounding","mock","http://127.0.0.1:11434/v1",
            client=client,max_steps=5,required_targets={"pricing.py"})
        self.assertIn("round(sum(values),2)",patch.patch)
        self.assertEqual(sum(t["action"]=="invalid_json_rejected"
                             for t in meta["tool_trace"]),3)
        self.assertFalse(any("not-json" in m["content"] or
                             "{invalid" in m["content"]
                             for hist in inputs for m in hist))

    def test_repeated_invalid_model_json_exhausts_bounded_budget(self):
        calls=[]
        def client(url,model,token,messages):
            calls.append(1)
            return {"choices":[{"message":{"content":"bad output"}}]}
        with self.assertRaisesRegex(AgentToolError,"after step budget"):
            propose_agentic_benchmark(
                self.repo,"fix rounding","mock","http://127.0.0.1:11434/v1",
                client=client,max_steps=3,required_targets={"pricing.py"})
        self.assertEqual(len(calls),3)

    def test_provider_transient_503_retries_then_returns_response(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return b'{"choices":[{"message":{"content":"{}"}}]}'
        class Opener:
            calls=0
            def open(self,*args,**kwargs):
                self.calls+=1
                if self.calls==1:
                    raise urllib.error.HTTPError("http://localhost",503,"unavailable",None,None)
                return Response()
        opener=Opener()
        with patch("repopilot.agentic_benchmark.urllib.request.build_opener",return_value=opener), patch("repopilot.agentic_benchmark.time.sleep"):
            result=_provider("http://127.0.0.1:11434/v1","mock",None,[])
        self.assertEqual(opener.calls,2)
        self.assertEqual(result["choices"][0]["message"]["content"],"{}")

    def test_provider_persistent_503_reports_code_without_leaking_url(self):
        class Opener:
            def open(self,*args,**kwargs):
                raise urllib.error.HTTPError("http://localhost/private?q=secret",503,"secret",None,None)
        with patch("repopilot.agentic_benchmark.urllib.request.build_opener",return_value=Opener()), patch("repopilot.agentic_benchmark.time.sleep"):
            with self.assertRaises(AgentToolError) as context:
                _provider("http://127.0.0.1:11434/v1","mock","TOP_SECRET_KEY",[])
        self.assertIn("HTTP 503 after 2 attempt",str(context.exception))
        self.assertNotIn("TOP_SECRET_KEY",str(context.exception))
        self.assertNotIn("private",str(context.exception))

    def test_provider_invalid_json_is_classified(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return b'not json'
        class Opener:
            def open(self,*args,**kwargs): return Response()
        with patch("repopilot.agentic_benchmark.urllib.request.build_opener",return_value=Opener()):
            with self.assertRaisesRegex(AgentToolError,"invalid JSON"):
                _provider("http://127.0.0.1:11434/v1","mock",None,[])

    def test_provider_missing_content_is_classified(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return b'{"choices":[{"message":{}}]}'
        class Opener:
            def open(self,*args,**kwargs): return Response()
        with patch("repopilot.agentic_benchmark.urllib.request.build_opener",return_value=Opener()):
            with self.assertRaisesRegex(AgentToolError,"missing choices"):
                _provider("http://127.0.0.1:11434/v1","mock",None,[])


    def test_initial_finish_inspects_target_and_requires_fresh_patch(self):
        first={"action":"finish","edits":[
            {"path":"pricing.py","old":"return sum(values)","new":"return 999"}]}
        second={"action":"finish","edits":[
            {"path":"pricing.py","old":"return sum(values)",
             "new":"return round(sum(values), 2)"}]}
        seen=[]
        it=iter([first,second])
        def client(url,model,token,messages):
            seen.append(list(messages))
            return {"choices":[{"message":{"content":json.dumps(next(it))}}]}
        patch,meta=propose_agentic_benchmark(
            self.repo,"round subtotal","mock","http://127.0.0.1:11434/v1",
            client=client,max_steps=2)
        self.assertIn("round(sum(values), 2)",patch.patch)
        self.assertNotIn("999",patch.patch)
        self.assertTrue(any(x["action"]=="initial_finish_preinspect"
                            for x in meta["tool_trace"]))
        self.assertEqual(meta["inspected_files"],["pricing.py"])
        self.assertTrue(any("return sum(values)" in item["content"]
                            for item in seen[1] if item["role"]=="user"))

    def test_initial_finish_does_not_inspect_unsafe_path(self):
        response={"action":"finish","edits":[
            {"path":"../outside.py","old":"x","new":"y"}]}
        with self.assertRaisesRegex(AgentToolError,
                                    "Cannot change source before inspecting files"):
            propose_agentic_benchmark(
                self.repo,"fix","mock","http://127.0.0.1:11434/v1",
                client=self.sequence([response]),max_steps=2)


    def test_local_ollama_native_fallback_after_compatible_api_404(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n):
                return json.dumps({
                    "message":{"content":'{"action":"list","prefix":""}'},
                    "eval_count":12}).encode()
        class Opener:
            def __init__(self): self.urls=[]
            def open(self,request,**kwargs):
                self.urls.append(request.full_url)
                if request.full_url.endswith("/v1/chat/completions"):
                    raise urllib.error.HTTPError(
                        request.full_url,404,"not found",None,None)
                self.assert_native(request)
                return Response()
            def assert_native(self,request):
                assert request.full_url.endswith("/api/chat")
        opener=Opener()
        with patch("repopilot.agentic_benchmark.urllib.request.build_opener",
                   return_value=opener):
            result=_provider("http://127.0.0.1:11434/v1",
                             "qwen2.5-coder:3b",None,[])
        self.assertEqual(len(opener.urls),2)
        self.assertEqual(result["choices"][0]["message"]["content"],
                         '{"action":"list","prefix":""}')
        self.assertEqual(result["usage"]["completion_tokens"],12)

    def test_404_on_non_ollama_endpoint_does_not_leak_source_to_fallback(self):
        class Opener:
            calls=0
            def open(self,request,**kwargs):
                self.calls+=1
                raise urllib.error.HTTPError(
                    request.full_url,404,"not found",None,None)
        opener=Opener()
        with patch("repopilot.agentic_benchmark.urllib.request.build_opener",
                   return_value=opener):
            with self.assertRaisesRegex(AgentToolError,"HTTP 404"):
                _provider("https://example.com/v1","mock","SECRET",[
                    {"role":"user","content":"source code"}])
        self.assertEqual(opener.calls,1)

    def test_read_two_modules_then_emit_valid_multi_file_patch(self):
        steps=[
            {"action":"list","prefix":""},
            {"action":"search","query":"subtotal"},
            {"action":"read","path":"pricing.py","start":1,"count":80},
            {"action":"read","path":"checkout.py","start":1,"count":80},
            {"action":"finish","edits":[
                {"path":"pricing.py","old":"return sum(values)","new":"return round(sum(values), 2)"},
                {"path":"checkout.py","old":"return subtotal(values)","new":"return round(subtotal(values), 2)"}
            ]}
        ]
        result,meta=propose_agentic_benchmark(self.repo,"round totals","mock",
            "http://127.0.0.1:11434/v1",client=self.sequence(steps))
        self.assertEqual(result.patch.count("diff --git"),2)
        self.assertEqual(meta["agent_steps"],5)
        self.assertEqual(meta["inspected_files"],["checkout.py","pricing.py"])
        self.assertEqual(len(meta["tool_trace"]),4)
    def test_defers_early_finish_until_all_required_files_changed(self):
        steps=[
            {"action":"read","path":"pricing.py"},
            {"action":"finish","edits":[{"path":"pricing.py","old":"return sum(values)","new":"return round(sum(values), 2)"}]},
            {"action":"read","path":"checkout.py"},
            {"action":"finish","edits":[{"path":"pricing.py","old":"return sum(values)","new":"return round(sum(values), 2)"}]},
            {"action":"finish","edits":[
                {"path":"pricing.py","old":"return sum(values)","new":"return round(sum(values), 2)"},
                {"path":"checkout.py","old":"return subtotal(values)","new":"return round(subtotal(values), 2)"}
            ]}
        ]
        patch,meta=propose_agentic_benchmark(self.repo,"both modules need rounding","mock",
            "http://127.0.0.1:11434/v1",client=self.sequence(steps),
            required_targets={"pricing.py","checkout.py"})
        self.assertEqual(patch.patch.count("diff --git"),2)
        self.assertEqual(meta["agent_steps"],5)
        self.assertEqual(sum(x["action"]=="finish_deferred" for x in meta["tool_trace"]),2)

    def test_required_files_are_preinspected_without_model_reads(self):
        steps=[{"action":"finish","edits":[
            {"path":"pricing.py","old":"return sum(values)","new":"return round(sum(values),2)"},
            {"path":"checkout.py","old":"return subtotal(values)","new":"return round(subtotal(values),2)"}
        ]}]
        captured=[]
        def client(url,model,token,messages):
            captured.extend(messages)
            return self.sequence(steps)(url,model,token,messages)
        patch,meta=propose_agentic_benchmark(self.repo,"round both modules",
            "mock","http://127.0.0.1:11434/v1",client=client,
            required_targets={"pricing.py","checkout.py"},max_steps=2)
        self.assertEqual(patch.patch.count("diff --git"),2)
        self.assertEqual(meta["agent_steps"],1)
        self.assertEqual([x["action"] for x in meta["tool_trace"]],
                         ["preinspect","preinspect","final_phase_started"])
        self.assertTrue(any("EXACT COMPLETE SOURCE" in m["content"] for m in captured))

    def test_malformed_finish_gets_bounded_correction(self):
        steps=[
            {"action":"read","path":"pricing.py"},
            {"action":"finish","edits":[{"path":"pricing.py","old":"not present","new":"x=3"}]},
            {"action":"finish","edits":[{"path":"pricing.py","old":"return sum(values)","new":"return sum(values)+1"}]}
        ]
        patch,meta=propose_agentic_benchmark(self.repo,"fix","mock",
            "http://127.0.0.1:11434/v1",client=self.sequence(steps),
            max_steps=4)
        self.assertIn("sum(values)+1",patch.patch)
        self.assertIn("finish_rejected",[x["action"] for x in meta["tool_trace"]])

    def test_rejects_unsafe_preinspection_target(self):
        with self.assertRaises(Exception):
            propose_agentic_benchmark(self.repo,"fix","mock",
                "http://127.0.0.1:11434/v1",client=self.sequence([]),
                required_targets={"../other.py"})

    def test_final_phase_forces_patch_without_more_tool_reads(self):
        calls=[]
        def client(url,model,token,messages):
            calls.append(list(messages))
            if len(calls)<=5:
                action={"action":"search","query":"taxable_subtotal"}
            else:
                self.assertIn("FINAL PATCH MODE",messages[0]["content"])
                action={"action":"finish","edits":[
                    {"path":"pricing.py","old":"return sum(values)",
                     "new":"return round(sum(values), 2)"},
                    {"path":"checkout.py","old":"return subtotal(values)",
                     "new":"return round(subtotal(values), 2)"}]}
            return {"choices":[{"message":{"content":json.dumps(action)}}],
                    "usage":{"total_tokens":7}}
        proposal,meta=propose_agentic_benchmark(
            self.repo,"round totals","mock","http://127.0.0.1:11434/v1",
            client=client,max_steps=10,required_targets={"pricing.py","checkout.py"})
        self.assertEqual(proposal.patch.count("diff --git"),2)
        self.assertEqual(meta["agent_steps"],6)
        self.assertIn("final_phase_started",[x["action"] for x in meta["tool_trace"]])

    def test_final_phase_rejects_repeated_exploration(self):
        response={"choices":[{"message":{"content":json.dumps(
            {"action":"search","query":"subtotal"})}}]}
        with self.assertRaisesRegex(AgentToolError,"action_counts"):
            propose_agentic_benchmark(
                self.repo,"fix","mock","http://127.0.0.1:11434/v1",
                client=lambda *args:response,max_steps=8,
                required_targets={"pricing.py","checkout.py"})

    def test_complete_file_mode_uses_only_model_generated_source(self):
        steps=[{"action":"finish","files":[
            {"path":"pricing.py","content":
             "def subtotal(values):\n    return round(sum(values),2)\n"},
            {"path":"checkout.py","content":
             "from pricing import subtotal\ndef total(values):\n"
             "    return round(subtotal(values),2)\n"}
        ]}]
        patch,meta=propose_agentic_benchmark(
            self.repo,"round totals","mock","http://127.0.0.1:11434/v1",
            client=self.sequence(steps),max_steps=2,
            required_targets={"pricing.py","checkout.py"})
        self.assertEqual(patch.patch.count("diff --git"),2)
        self.assertEqual(meta["agent_steps"],1)

    def test_complete_file_mode_refuses_uninspected_file(self):
        steps=[{"action":"finish","files":[
            {"path":"../checkout.py","content":"x=2\n"}]}]
        with self.assertRaises(AgentToolError):
            propose_agentic_benchmark(self.repo,"fix","mock",
                "http://127.0.0.1:11434/v1",client=self.sequence(steps),
                max_steps=2)

    def test_complete_file_mode_rejects_invalid_syntax_then_corrects(self):
        steps=[
            {"action":"finish","files":[
                {"path":"pricing.py","content":"def broken(:\n"},
                {"path":"checkout.py","content":"x=1\n"}]},
            {"action":"finish","files":[
                {"path":"pricing.py","content":
                    "def subtotal(values):\n    return round(sum(values),2)\n"},
                {"path":"checkout.py","content":
                    "from pricing import subtotal\ndef total(values):\n"
                    "    return round(subtotal(values),2)\n"}]}
        ]
        patch,meta=propose_agentic_benchmark(
            self.repo,"fix","mock","http://127.0.0.1:11434/v1",
            client=self.sequence(steps),max_steps=3,
            required_targets={"pricing.py","checkout.py"})
        self.assertEqual(patch.patch.count("diff --git"),2)
        self.assertIn("finish_rejected",[x["action"] for x in meta["tool_trace"]])

    def test_exact_mismatch_feedback_explains_correction(self):
        responses=[
            {"action":"finish","edits":[
                {"path":"pricing.py","old":"missing original snippet","new":"x=1"}]},
            {"action":"finish","files":[
                {"path":"pricing.py","content":
                    "def subtotal(values):\n    return round(sum(values), 2)\n"},
                {"path":"checkout.py","content":
                    "from pricing import subtotal\ndef total(values):\n"
                    "    return round(subtotal(values), 2)\n"}]}
        ]
        seen=[]
        it=iter(responses)
        def client(url,model,token,messages):
            seen.append(list(messages))
            return {"choices":[{"message":{"content":json.dumps(next(it))}}]}
        patch,meta=propose_agentic_benchmark(self.repo,"round totals","mock",
            "http://127.0.0.1:11434/v1",client=client,
            max_steps=3,required_targets={"pricing.py","checkout.py"})
        self.assertEqual(patch.patch.count("diff --git"),2)
        reasons=[item.get("reason","") for item in meta["tool_trace"]]
        self.assertTrue(any("does not match" in reason for reason in reasons))
        self.assertTrue(any("Previous candidate error" in item["content"]
                            for item in seen[1]))

    def test_complete_source_without_trailing_newline_normalized(self):
        response={"action":"finish","files":[
            {"path":"pricing.py","content":
                "def subtotal(values):\n    return round(sum(values), 2)"},
            {"path":"checkout.py","content":
                "from pricing import subtotal\ndef total(values):\n"
                "    return round(subtotal(values), 2)"}]}
        patch,_=propose_agentic_benchmark(self.repo,"round totals","mock",
            "http://127.0.0.1:11434/v1",client=self.sequence([response]),
            max_steps=2,required_targets={"pricing.py","checkout.py"})
        self.assertEqual(patch.patch.count("diff --git"),2)

    def test_exhaustion_exposes_rejection_reason_without_candidate_source(self):
        invalid={"action":"finish","edits":[
            {"path":"pricing.py","old":"not in source","new":"private_marker=1"}]}
        with self.assertRaises(AgentToolError) as context:
            propose_agentic_benchmark(self.repo,"fix","mock",
                "http://127.0.0.1:11434/v1",
                client=lambda *a:{"choices":[{"message":{"content":json.dumps(invalid)}}]},
                max_steps=3,required_targets={"pricing.py","checkout.py"})
        self.assertIn("rejection_reasons=",str(context.exception))
        self.assertIn("does not match",str(context.exception))
        self.assertNotIn("private_marker",str(context.exception))


    def test_large_source_final_prompt_keeps_deep_inspected_window(self):
        # The bug is far beyond the first 6 KB of a large source file.
        large="".join(
            f"DATA_{i} = 'padding to represent a realistic large source module'\n"
            for i in range(190)
        )+"def affected():\n    return 1\n"
        (self.repo/"large.py").write_text(large)
        calls=[]
        def client(url,model,token,messages):
            calls.append(list(messages))
            if len(calls)<=6:
                action={"action":"read","path":"large.py",
                        "start":175,"count":35}
            else:
                self.assertIn("FINAL PATCH MODE",messages[0]["content"])
                final=messages[-1]["content"]
                self.assertIn("def affected():",final)
                self.assertIn("return 1",final)
                self.assertNotIn("DATA_0 =",final)
                action={"action":"finish","edits":[
                    {"path":"large.py","old":"    return 1",
                     "new":"    return 2"}]}
            return {"choices":[{"message":{"content":json.dumps(action)}}]}
        patch,meta=propose_agentic_benchmark(
            self.repo,"fix affected()","mock",
            "http://127.0.0.1:11434/v1",
            client=client,max_steps=8)
        self.assertIn("+    return 2",patch.patch)
        self.assertEqual(meta["agent_steps"],7)


    def test_symbol_ranked_source_is_inspected_before_first_model_call(self):
        (self.repo/"billing.py").write_text(
            "def calculate_invoice_tax(amount):\n    return amount * 0.2\n")
        seen=[]
        def client(url,model,token,messages):
            seen.append(list(messages))
            answer={"action":"finish","edits":[{
                "path":"billing.py","old":"return amount * 0.2",
                "new":"return amount * 0.1"}]}
            return {"choices":[{"message":{"content":json.dumps(answer)}}]}
        patch,meta=propose_agentic_benchmark(
            self.repo,"Fix calculate_invoice_tax rounding","mock",
            "http://127.0.0.1:11434/v1",client=client,max_steps=2,
            auto_issue_paths=True)
        self.assertIn("amount * 0.1",patch.patch)
        self.assertIn("ranked_initial_preinspect",
                      [x["action"] for x in meta["tool_trace"]])
        self.assertTrue(any("billing.py" in m["content"] for m in seen[0]))

    def test_unscoped_benchmark_forces_patch_after_bounded_search(self):
        calls=[]
        def client(url,model,token,messages):
            calls.append(list(messages))
            if len(calls)<=6:
                value={"action":"read","path":"pricing.py"}
            else:
                self.assertIn("FINAL PATCH MODE",messages[0]["content"])
                value={"action":"finish","files":[{
                    "path":"pricing.py",
                    "content":"def subtotal(values):\n    return round(sum(values), 2)\n"}]}
            return {"choices":[{"message":{"content":json.dumps(value)}}]}
        patch,meta=propose_agentic_benchmark(self.repo,"round subtotal","mock",
            "http://127.0.0.1:11434/v1",client=client,max_steps=8)
        self.assertIn("return round",patch.patch)
        self.assertEqual(meta["agent_steps"],7)
        self.assertIn("final_phase_started",
                      [x["action"] for x in meta["tool_trace"]])

    def test_unscoped_benchmark_recovers_from_invalid_tool_paths(self):
        calls=[]
        def client(url,model,token,messages):
            calls.append(list(messages))
            if len(calls)<=6:
                value={"action":"read","path":"does_not_exist.py"}
            else:
                self.assertIn("FINAL PATCH MODE",messages[0]["content"])
                value={"action":"finish","edits":[{
                    "path":"pricing.py","old":"return sum(values)",
                    "new":"return round(sum(values), 2)"}]}
            return {"choices":[{"message":{"content":json.dumps(value)}}]}
        patch,meta=propose_agentic_benchmark(self.repo,
            "Fix pricing.py subtotal rounding","mock",
            "http://127.0.0.1:11434/v1",client=client,max_steps=8)
        self.assertIn("round(sum(values)",patch.patch)
        self.assertIn("ranked_preinspect",
                      [x["action"] for x in meta["tool_trace"]])

    def test_auto_preinspection_accepts_positive_body_evidence(self):
        observed=[]
        def client(url,model,token,messages):
            observed.append(list(messages))
            return {"choices":[{"message":{"content":json.dumps({
                "action":"finish","edits":[{
                    "path":"pricing.py","old":"return sum(values)",
                    "new":"return round(sum(values), 2)"}]})}}]}
        patch,meta=propose_agentic_benchmark(
            self.repo,"values","mock","http://127.0.0.1:11434/v1",
            client=client,max_steps=4,auto_issue_paths=True)
        self.assertIn("round(sum(values), 2)",patch.patch)
        self.assertTrue(any(x["action"]=="ranked_initial_preinspect"
                            for x in meta["tool_trace"]))
        self.assertTrue(any("SOURCE CANDIDATE" in m["content"]
                            for m in observed[0]))

    def test_early_invented_file_recovers_via_ranked_existing_source(self):
        steps=[
            {"action":"finish","edits":[{
                "path":"invented.py","old":"x = 1","new":"x = 2"}]},
            {"action":"finish","edits":[{
                "path":"pricing.py","old":"return sum(values)",
                "new":"return round(sum(values), 2)"}]}
        ]
        patch,meta=propose_agentic_benchmark(
            self.repo,"fix pricing.py subtotal","mock",
            "http://127.0.0.1:11434/v1",client=self.sequence(steps),
            max_steps=4)
        self.assertIn("round(sum(values), 2)",patch.patch)
        self.assertIn("pricing.py",meta["inspected_files"])
        self.assertNotIn("invented.py",meta["inspected_files"])
        self.assertTrue(any(x["action"]=="initial_finish_preinspect"
                            for x in meta["tool_trace"]))
        self.assertFalse((self.repo/"invented.py").exists())

    def test_early_invented_file_without_ranked_match_requests_real_read(self):
        steps=[
            {"action":"finish","edits":[{
                "path":"not_there.py","old":"x=1","new":"x=2"}]},
            {"action":"read","path":"pricing.py"},
            {"action":"finish","edits":[{
                "path":"pricing.py","old":"return sum(values)",
                "new":"return round(sum(values), 2)"}]}
        ]
        observed=[]
        it=iter(steps)
        def client(url,model,token,messages):
            observed.append(list(messages))
            return {"choices":[{"message":{"content":json.dumps(next(it))}}]}
        patch,meta=propose_agentic_benchmark(
            self.repo,"zzunlikelydomaintermzz","mock",
            "http://127.0.0.1:11434/v1",client=client,max_steps=5)
        self.assertIn("round(sum(values), 2)",patch.patch)
        self.assertIn("finish_rejected_no_source",
            [x["action"] for x in meta["tool_trace"]])
        self.assertTrue(any("next reply MUST" in m["content"] for m in observed[1]))

    def test_opt_in_issue_paths_preinspected_before_model_call(self):
        seen=[]
        def client(url,model,token,messages):
            seen.append(list(messages))
            return {"choices":[{"message":{"content":json.dumps({
                "action":"finish","edits":[{
                    "path":"pricing.py","old":"return sum(values)",
                    "new":"return round(sum(values),2)"}]})}}]}
        patch,meta=propose_agentic_benchmark(
            self.repo,"Please fix `pricing.py` subtotal rounding",
            "mock","http://127.0.0.1:11434/v1",
            client=client,max_steps=2,auto_issue_paths=True)
        self.assertIn("round(sum(values),2)",patch.patch)
        self.assertIn("pricing.py",meta["inspected_files"])
        self.assertTrue(any(x["action"]=="issue_path_preinspect"
                            for x in meta["tool_trace"]))
        self.assertIn("FINAL PATCH MODE",seen[0][0]["content"])

    def test_opt_in_issue_paths_rejects_unsafe_filename(self):
        response={"choices":[{"message":{"content":json.dumps({
            "action":"read","path":"pricing.py"})}}]}
        with self.assertRaises(AgentToolError):
            propose_agentic_benchmark(
                self.repo,"Do not read ../out_of_repo.py",
                "mock","http://127.0.0.1:11434/v1",
                client=lambda *a:response,max_steps=2,
                auto_issue_paths=True)

    def test_refuses_to_modify_uninspected_file(self):
        steps=[
            {"action":"read","path":"pricing.py"},
            {"action":"finish","edits":[{"path":"checkout.py","old":"return subtotal(values)","new":"return 4"}]}
        ]
        with self.assertRaises(AgentToolError):
            propose_agentic_benchmark(self.repo,"fix","mock","http://127.0.0.1:11434/v1",
                                     client=self.sequence(steps),max_steps=2)

    def test_uninspected_target_is_rejected_then_corrected(self):
        steps=[
            {"action":"read","path":"pricing.py"},
            {"action":"finish","edits":[
                {"path":"checkout.py","old":"return subtotal(values)","new":"return 4"}]},
            {"action":"finish","edits":[
                {"path":"pricing.py","old":"return sum(values)",
                 "new":"return round(sum(values),2)"}]}
        ]
        patch,meta=propose_agentic_benchmark(
            self.repo,"correct subtotal","mock","http://127.0.0.1:11434/v1",
            client=self.sequence(steps),max_steps=4)
        self.assertIn("round(sum(values),2)",patch.patch)
        self.assertTrue(any(
            step.get("error_type")=="UninspectedPatchTarget"
            for step in meta["tool_trace"]))

    def test_candidate_path_is_inspected_before_new_proposal(self):
        """First unsafe patch is discarded; second must use inspected source."""
        steps=[
            {"action":"read","path":"pricing.py"},
            {"action":"finish","edits":[
                {"path":"checkout.py","old":"return subtotal(values)",
                 "new":"return round(subtotal(values),2)"}]},
            {"action":"finish","edits":[
                {"path":"checkout.py","old":"return subtotal(values)",
                 "new":"return round(subtotal(values),2)"}]}
        ]
        seen=[]
        it=iter(steps)
        def client(url,model,token,messages):
            seen.append(list(messages))
            return {"choices":[{"message":{"content":json.dumps(next(it))}}]}
        result,meta=propose_agentic_benchmark(
            self.repo,"round invoice totals","mock","http://127.0.0.1:11434/v1",
            client=client,max_steps=4)
        self.assertIn("round(subtotal(values),2)",result.patch)
        self.assertEqual(meta["inspected_files"],["checkout.py","pricing.py"])
        self.assertTrue(any(x.get("action")=="candidate_preinspect"
                            and x.get("target")=="checkout.py"
                            for x in meta["tool_trace"]))
        self.assertTrue(any("Your previous candidate was REJECTED" in m["content"]
                            and "return subtotal(values)" in m["content"]
                            for m in seen[2]))

    def test_candidate_inspection_rejects_traversal_and_missing_paths(self):
        steps=[
            {"action":"read","path":"pricing.py"},
            {"action":"finish","edits":[
                {"path":"../outside.py","old":"x=1","new":"x=2"}]},
            {"action":"finish","edits":[
                {"path":"pricing.py","old":"return sum(values)",
                 "new":"return round(sum(values),2)"}]}
        ]
        result,meta=propose_agentic_benchmark(
            self.repo,"round subtotal","mock","http://127.0.0.1:11434/v1",
            client=self.sequence(steps),max_steps=4)
        self.assertIn("round(sum(values),2)",result.patch)
        self.assertNotIn("../outside.py",meta["inspected_files"])
        self.assertFalse(any(x.get("action")=="candidate_preinspect"
                             for x in meta["tool_trace"]))

    def test_forbids_model_shell_access(self):
        with self.assertRaises(AgentToolError):
            propose_agentic_benchmark(self.repo,"fix","mock","http://127.0.0.1:11434/v1",
                    client=self.sequence([{"action":"shell","command":"echo secret"}]))
    def test_enforces_bounded_steps(self):
        with self.assertRaises(AgentToolError):
            propose_agentic_benchmark(self.repo,"fix","mock","http://127.0.0.1:11434/v1",
                client=self.sequence([{"action":"list"}]*4),max_steps=4)
if __name__=="__main__":
    unittest.main()
