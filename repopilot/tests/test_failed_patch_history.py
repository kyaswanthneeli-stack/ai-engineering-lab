"""Regression coverage for rejecting previously failed autonomous patches."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repopilot.agentic_benchmark import AgentToolError, propose_agentic_benchmark
from repopilot.edit_plan import canonical_patch


class FailedPatchHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        (self.repo / "pricing.py").write_text(
            "def total(values):\n    return sum(values)\n", encoding="utf-8"
        )

    def candidate(self, replacement):
        return {"action": "finish", "edits": [{
            "path": "pricing.py", "old": "return sum(values)",
            "new": replacement,
        }]}

    def fingerprint(self, replacement):
        generated = canonical_patch(self.repo, [{
            "path": "pricing.py", "old": "return sum(values)",
            "new": replacement,
        }], allowed_files={"pricing.py"})
        return hashlib.sha256(generated.encode("utf-8")).hexdigest()

    def agent(self, choices, hashes, *, max_steps=3):
        call_history = []
        actions = iter(choices)

        def model(url, model_name, token, messages):
            call_history.append([dict(m) for m in messages])
            return {"choices": [{"message": {
                "content": json.dumps(next(actions))
            }}]}

        with patch.dict("os.environ", {"REPOPILOT_CANDIDATE_SMOKE": "0"}):
            result = propose_agentic_benchmark(
                self.repo, "Fix total rounding", "mock",
                "http://127.0.0.1:11434/v1", client=model,
                max_steps=max_steps, required_targets={"pricing.py"},
                rejected_patch_sha256s=hashes,
            )
        return result, call_history

    def test_known_failed_patch_is_rejected_and_different_patch_is_returned(self):
        failed = self.fingerprint("return sum(values) + 1")
        (candidate, metadata), history = self.agent(
            [self.candidate("return sum(values) + 1"),
             self.candidate("return sum(values) + 2")], {failed}
        )
        self.assertEqual(len(history), 2)
        self.assertIn("+ 2", candidate.patch)
        self.assertNotEqual(
            hashlib.sha256(candidate.patch.encode("utf-8")).hexdigest(), failed
        )
        self.assertEqual(
            [step["action"] for step in metadata["tool_trace"]].count(
                "duplicate_failed_patch_rejected"), 1
        )
        self.assertTrue(any(
            "already tried and failed" in message["content"]
            for message in history[1]
        ))

    def test_repeated_failed_patch_exhausts_budget_without_submission(self):
        failed = self.fingerprint("return sum(values) + 1")
        with self.assertRaisesRegex(AgentToolError, "Previously failed patch repeated"):
            self.agent(
                [self.candidate("return sum(values) + 1")] * 2,
                {failed}, max_steps=2
            )

    def test_invalid_prior_hash_fails_before_model_request(self):
        with self.assertRaisesRegex(AgentToolError, "Invalid previously failed patch SHA-256"):
            self.agent([], {"not-a-sha256"})
