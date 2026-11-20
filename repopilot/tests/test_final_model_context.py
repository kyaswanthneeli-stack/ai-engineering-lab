"""Verify compact, honest model source prompts for small CPU models.

No deterministic fixture outcome is labeled as an official SWE-bench pass.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repopilot.agentic_benchmark import (
    _compact_final_context, _model_source_budget,
    propose_agentic_benchmark, AgentToolError
)


class FinalContextBudgetTests(unittest.TestCase):
    def test_full_source_context_is_unchanged_when_inside_budget(self):
        items=["EXACT COMPLETE SOURCE a.py:\nx=1\n",
               "EXACT COMPLETE SOURCE b.py:\ny=2\n"]
        self.assertEqual(_compact_final_context(items,4500),items)

    def test_oversized_context_has_strict_total_budget_and_clear_excerpts(self):
        items=[
            "EXACT COMPLETE SOURCE invoice.py:\n"+("x = 1\n"*1100),
            "EXACT COMPLETE SOURCE checkout.py:\n"+("y = 2\n"*1100),
            "EXACT COMPLETE SOURCE main.py:\n"+("z = 3\n"*1100)
        ]
        result=_compact_final_context(items,9000)
        self.assertLessEqual(len("\n\n".join(result)),9000)
        self.assertEqual(len(result),3)
        for name,chunk in zip(("invoice.py","checkout.py","main.py"),result):
            self.assertIn(name,chunk)
            self.assertNotIn("EXACT COMPLETE SOURCE",chunk)
            self.assertIn("source excerpt shortened",chunk)
            self.assertIn("use exact edits",chunk)

    def test_invalid_configuration_rejected(self):
        for setting in ("", "bad", "4499", "24001", "-8"):
            with self.subTest(setting=setting), patch.dict(
                    "os.environ",{"REPOPILOT_FINAL_CONTEXT_CHARS":setting}):
                with self.assertRaisesRegex(
                        AgentToolError,"final source context|Final source context"):
                    _model_source_budget()

    def test_agentic_benchmark_model_receives_compacted_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            # A long, otherwise-valid source file with a relevant bug at top.
            source=("def compute_tax(price):\n    return price\n"+
                    ("# auxiliary context that should not dominate inference\n"*145))
            self.assertGreater(len(source),6000)
            (root/"pricing.py").write_text(source)
            requested=[]
            outputs=iter([
                {"action":"list","prefix":""},
                {"action":"list","prefix":""},
                {"action":"finish","edits":[{
                    "path":"pricing.py",
                    "old":"return price",
                    "new":"return round(price * 1.1, 2)"
                }]}
            ])
            def client(url,model,token,messages):
                requested.append(list(messages))
                return {"choices":[{"message":{"content":json.dumps(next(outputs))}}]}
            with patch.dict("os.environ",{
                    "REPOPILOT_FINAL_CONTEXT_CHARS":"4500",
                    "REPOPILOT_AGENT_BUDGET_SECONDS":"0"}):
                result,meta=propose_agentic_benchmark(
                    root,"Correct compute_tax in pricing.py", "qwen-test",
                    "http://127.0.0.1:11434/v1", client=client,
                    max_steps=4, auto_issue_paths=True)
            self.assertEqual(meta["agent_steps"],3)
            self.assertIn("round(price * 1.1, 2)",result.patch)
            final_prompt=requested[-1][-1]["content"]
            self.assertIn("SOURCE EXCERPT pricing.py",final_prompt)
            self.assertIn("source excerpt shortened",final_prompt)
            self.assertNotIn("EXACT COMPLETE SOURCE",final_prompt)
            self.assertIn("small",requested[-1][0]["content"].lower())
            self.assertLess(len(final_prompt),9000)


if __name__=="__main__":
    unittest.main()
