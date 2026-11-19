import json
import tempfile
import unittest
from pathlib import Path
from repopilot.agentic_benchmark import propose_agentic_benchmark,AgentToolError


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
            {"path":"checkout.py","content":"x=2\n"}]}]
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

    def test_refuses_to_modify_uninspected_file(self):
        steps=[
            {"action":"read","path":"pricing.py"},
            {"action":"finish","edits":[{"path":"checkout.py","old":"return subtotal(values)","new":"return 4"}]}
        ]
        with self.assertRaises(ValueError):
            propose_agentic_benchmark(self.repo,"fix","mock","http://127.0.0.1:11434/v1",
                                     client=self.sequence(steps))
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
