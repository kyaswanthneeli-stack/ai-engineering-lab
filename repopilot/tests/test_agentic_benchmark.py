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
