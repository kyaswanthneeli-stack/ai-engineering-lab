"""Synthetic localization fixtures; no benchmark reference patch or target path."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from repopilot.context_select import issue_identifiers, identifier_window, ranked_source_context
from repopilot.agentic_benchmark import propose_agentic_benchmark

class IdentifierLocalizationTests(unittest.TestCase):
    def test_exact_identifier_extraction_and_deep_window(self):
        identifiers=issue_identifiers("Issue with QUEUE_MODE and flush_buffer. flush_buffer fails.")
        self.assertEqual(set(identifiers), {"QUEUE_MODE","flush_buffer"})
        self.assertEqual(identifiers[0],"flush_buffer")
        source="# filler\n"*180+"def flush_buffer():\n    return QUEUE_MODE\n"
        start=identifier_window(source, identifiers,count=80)
        self.assertGreater(start,1)
        self.assertIn("def flush_buffer", "\n".join(source.splitlines()[start-1:start+79]))

    def test_exact_body_hit_can_outrank_generic_path_and_symbol_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"request_response.py").write_text("def request(): pass\ndef response(): pass\n")
            (root/"worker.py").write_text("# filler\n"*180+"value = QUEUE_MODE\n")
            for i in range(10):
                (root/f"common_{i}.py").write_text("# request response\n")
            with patch.dict("os.environ",{"REPOPILOT_IDENTIFIER_LOCALIZATION":"1",
                                         "REPOPILOT_WEIGHT_RARE_TERMS":"1"}):
                items=ranked_source_context(root,"request response QUEUE_MODE",max_files=2)
            self.assertEqual(items[0].path,"worker.py")

    def test_failed_search_recovery_exposes_only_existing_paths_and_issue_identifiers(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source="# filler\n"*180+"def flush_buffer():\n    return 1\n"
            (root/"worker.py").write_text(source)
            actions=iter([{"action":"search","query":"literal code token"},
                          {"action":"read","path":"worker.py","start":170,"count":20},
                          {"action":"finish","edits":[{"path":"worker.py","old":"return 1","new":"return 2"}]}])
            history=[]
            def client(*args):
                history.append(list(args[-1]))
                return {"choices":[{"message":{"content":json.dumps(next(actions))}}]}
            with patch.dict("os.environ",{"REPOPILOT_IDENTIFIER_LOCALIZATION":"1",
                                         "REPOPILOT_CONFIRM_RANKED_SOURCE":"1",
                                         "REPOPILOT_CANDIDATE_SMOKE":"0"}):
                candidate,meta=propose_agentic_benchmark(root,"flush_buffer returns wrong value",
                    "mock","http://127.0.0.1:11434/v1",client=client,max_steps=6,auto_issue_paths=True)
            self.assertIn("return 2",candidate.patch)
            self.assertIn("empty_discovery_recovery",[e["action"] for e in meta["tool_trace"]])
            self.assertIn("issue_identifiers", history[1][-1]["content"])
            self.assertNotIn("existing.py",history[0][0]["content"])
            self.assertEqual((root/"worker.py").read_text(),source)
