"""Automated tests covering dispatch, polling, artifact retrieval, auth, quotas, and verification outcomes."""

from __future__ import annotations

import io
import hashlib
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "hf_space"))

import app as hf_app  # noqa: E402


class _FakeResp:
    def __init__(self, data: bytes, status: int = 200) -> None:
        self._data = data
        self.status = status

    def read(self, n: int = -1) -> bytes:
        return self._data if n < 0 else self._data[:n]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestHuggingFaceSpace(unittest.TestCase):
    def setUp(self) -> None:
        environment = patch.dict(os.environ, {"REPOPILOT_ACCESS_TOKEN": "fixture-access", "GITHUB_TOKEN": "fixture-runner"})
        environment.start()
        self.addCleanup(environment.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.quota_path = Path(self.tmp.name) / "quota.json"
        self.store = hf_app.JobStore(max_jobs=10)
        self.limiter = hf_app.RateLimiter(max_requests=5, window_seconds=60)
        self.quota = hf_app.PersistentDailyQuota(self.quota_path, max_daily_jobs=20)
        self.outcome_mode = "verified_in_sandbox"
        self.dispatched_calls: list[tuple] = []

        def fake_resolver(owner, repo, number):
            return "ZeroDivisionError in calc", "a" * 40

        def fake_dispatcher(owner, repo, number, base_sha, job_id):
            self.dispatched_calls.append((owner, repo, number, base_sha, job_id))
            return True, f"https://github.com/{owner}/{repo}/actions/workflows/repopilot-remote-issue-agent.yml"

        def fake_poller(runner_repo, job_id, **kwargs):
            if self.outcome_mode == "failed_verification":
                return {
                    "job_id": job_id,
                    "outcome": "failed_verification",
                    "failed_stage": "patched_tests",
                    "patch": "diff --git a/c.py b/c.py\n--- a/c.py\n+++ b/c.py\n@@ -1 +1 @@\n-x=1\n+x=2\n",
                    "before_tests": {"exit_code": 1, "output": "ZeroDivisionError"},
                    "after_tests": {"exit_code": 1, "output": "AssertionError: still failing"},
                    "workflow_run_id": 999,
                    "workflow_url": "https://github.com/org/repo/actions/runs/999",
                }
            return {
                "job_id": job_id,
                "outcome": "verified_in_sandbox",
                "failed_stage": "",
                "patch": "diff --git a/c.py b/c.py\n--- a/c.py\n+++ b/c.py\n@@ -1 +1 @@\n-return a/b\n+return 0 if b==0 else a/b\n",
                "before_tests": {"exit_code": 1, "output": "ZeroDivisionError"},
                "after_tests": {"exit_code": 0, "output": "OK (1 test)"},
                "workflow_run_id": 1000,
                "workflow_url": "https://github.com/org/repo/actions/runs/1000",
            }

        handler_cls = hf_app.make_handler(
            self.store,
            self.limiter,
            self.quota,
            max_concurrent_jobs=2,
            allowed_target=None,
            issue_resolver=fake_resolver,
            verifier_dispatcher=fake_dispatcher,
            result_poller=fake_poller,
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def _req(self, path: str, *, method: str = "GET", body: dict | None = None, headers: dict | None = None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            headers={"X-RepoPilot-Token": "fixture-access", **(headers or {})},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, dict(resp.headers), resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read().decode("utf-8")

    def test_download_redirect_never_forwards_github_authorization(self):
        req = urllib.request.Request("https://api.github.com/fixture", headers={"Authorization": "Bearer test"})
        redirect = hf_app._ArtifactRedirect().redirect_request(
            req, None, 302, "Redirect", {}, "https://fixture.blob.core.windows.net/result")
        self.assertIsNone(redirect.get_header("Authorization"))

    def test_successful_dispatch_verification_and_job_authorization(self) -> None:
        st, _, raw = self._req(
            "/api/jobs",
            method="POST",
            body={"issue_url": "https://github.com/org/repo/issues/42"},
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(st, 202)
        created = json.loads(raw)
        job_id = created["job_id"]
        job_token = created["job_token"]

        # Unauthorized polling/report download without X-Job-Token must fail closed (403)
        st_no_auth, _, _ = self._req(f"/api/jobs/{job_id}")
        self.assertEqual(st_no_auth, 403)
        st_rep_no_auth, _, _ = self._req(f"/api/jobs/{job_id}/report")
        self.assertEqual(st_rep_no_auth, 403)

        job = {}
        for _ in range(30):
            st_poll, _, jr = self._req(f"/api/jobs/{job_id}", headers={"X-Job-Token": job_token})
            self.assertEqual(st_poll, 200)
            job = json.loads(jr)
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.02)

        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["outcome"], "verified_in_sandbox")
        self.assertEqual(job["base_sha"], "a" * 40)
        self.assertEqual(self.dispatched_calls[0], ("org", "repo", 42, "a" * 40, job_id))
        self.assertEqual(job["before_tests"]["status"], "exit_1")
        self.assertEqual(job["after_tests"]["status"], "exit_0")

        # Authorized report download
        st_rep, hdrs, md = self._req(f"/api/jobs/{job_id}/report", headers={"X-Job-Token": job_token})
        self.assertEqual(st_rep, 200)
        self.assertIn("attachment", hdrs.get("Content-Disposition", ""))
        self.assertIn("a" * 40, md)

    def test_failed_verification_outcome_propagated(self) -> None:
        self.outcome_mode = "failed_verification"
        st, _, raw = self._req(
            "/api/jobs",
            method="POST",
            body={"issue_url": "https://github.com/org/repo/issues/43"},
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(st, 202)
        created = json.loads(raw)
        job_id, job_token = created["job_id"], created["job_token"]

        job = {}
        for _ in range(30):
            _, _, jr = self._req(f"/api/jobs/{job_id}", headers={"X-Job-Token": job_token})
            job = json.loads(jr)
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.02)

        self.assertEqual(job["status"], "failed")
        self.assertEqual(job["outcome"], "failed_verification")
        self.assertIn("still failing", job["after_tests"]["summary"])

    def test_poll_and_fetch_result_retrieves_artifact_zip(self) -> None:
        job_id = "0123456789abcdef"
        patch_text = "diff --git a/a.py b/a.py\n"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                f"repopilot-result-{job_id}.json",
                json.dumps({"job_id": job_id, "outcome": "verified_in_sandbox", "patch": patch_text,
                            "patch_sha256": hashlib.sha256(patch_text.encode()).hexdigest(),
                            "model_generated_proposal": True, "baseline": {"exit_code": 0},
                            "before_tests": {"exit_code": 1}, "after_tests": {"exit_code": 0}}),
            )
        zip_bytes = buf.getvalue()

        call_state = {"poll": 0}

        class FakeOpener:
            def open(self, req, timeout=15):
                u = req.full_url
                if u.endswith("/runs?event=workflow_dispatch&per_page=15"):
                    call_state["poll"] += 1
                    status = "in_progress" if call_state["poll"] == 1 else "completed"
                    return _FakeResp(
                        json.dumps({"workflow_runs": [{"id": 55, "status": status, "conclusion": "success", "display_title": f"RepoPilot demo {job_id}", "html_url": "https://github.com/o/r/actions/runs/55"}]}).encode()
                    )
                if u.endswith("/actions/runs/55/artifacts"):
                    return _FakeResp(
                        json.dumps({"artifacts": [{"name": f"repopilot-result-{job_id}", "id": 55}]}).encode()
                    )
                return _FakeResp(zip_bytes)

        stages: list[str] = []
        res = hf_app.poll_and_fetch_result(
            "o/r",
            job_id,
            github_token="tok",
            opener=FakeOpener(),
            artifact_opener=FakeOpener(),
            deadline_seconds=10,
            poll_interval=0.01,
            on_progress=lambda st, pct: stages.append(st),
        )
        self.assertEqual(res["outcome"], "verified_in_sandbox")
        self.assertEqual(res["workflow_run_id"], 55)
        self.assertIn("github_actions_in_progress", stages)

    def test_untrusted_x_forwarded_for_cannot_bypass_rate_limit(self) -> None:
        # Even with rotating X-Forwarded-For headers, rate limiter keys on real peer IP (127.0.0.1)
        for i in range(5):
            st, _, _ = self._req(
                "/api/jobs",
                method="POST",
                body={"issue_url": f"https://github.com/org/repo/issues/{i+1}"},
                headers={"Content-Type": "application/json", "X-Forwarded-For": f"198.51.100.{i+1}"},
            )
            self.assertEqual(st, 202)
        st_limited, _, _ = self._req(
            "/api/jobs",
            method="POST",
            body={"issue_url": "https://github.com/org/repo/issues/99"},
            headers={"Content-Type": "application/json", "X-Forwarded-For": "198.51.100.250"},
        )
        self.assertEqual(st_limited, 429)

    def test_persistent_quota_fails_closed_on_corrupt_storage(self) -> None:
        self.quota_path.write_text("{corrupt json", encoding="utf-8")
        st, _, raw = self._req(
            "/api/jobs",
            method="POST",
            body={"issue_url": "https://github.com/org/repo/issues/1"},
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(st, 503)
        self.assertIn("failing closed", raw)

    def test_authentication_fails_closed_and_dispatch_is_fixture_only(self):
        with patch.dict(os.environ, {"REPOPILOT_ACCESS_TOKEN": ""}):
            status, _, _ = self._req("/api/jobs", method="POST")
        self.assertEqual(status,401)
        with self.assertRaisesRegex(ValueError, "calculator fixture"):
            hf_app.dispatch_remote_verification("org","repo",1,"a"*40,"b"*16)

    def test_timeout_missing_artifact_quota_exhaustion_and_recursive_redaction(self) -> None:
        # 1. Timeout propagation
        def timeout_poller(*args, **kwargs):
            raise TimeoutError("Timed out waiting for remote verification artifact")

        store2 = hf_app.JobStore(max_jobs=10)
        lim2 = hf_app.RateLimiter(max_requests=10, window_seconds=60)
        q2 = hf_app.PersistentDailyQuota(Path(self.tmp.name) / "q2.json", max_daily_jobs=1)
        srv2 = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            hf_app.make_handler(
                store2,
                lim2,
                q2,
                allowed_target=None,
                issue_resolver=lambda o, r, n: ("t", "b" * 40),
                verifier_dispatcher=lambda o, r, n, s, j: (True, "https://github.com/o/r/actions"),
                result_poller=timeout_poller,
            ),
        )
        t2 = threading.Thread(target=srv2.serve_forever, daemon=True)
        t2.start()
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{srv2.server_port}/api/jobs",
                data=json.dumps({"issue_url": "https://github.com/org/repo/issues/1"}).encode(),
                headers={"Content-Type": "application/json", "X-RepoPilot-Token": "fixture-access"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                created = json.loads(resp.read().decode())
            job = {}
            for _ in range(30):
                greq = urllib.request.Request(
                    f"http://127.0.0.1:{srv2.server_port}/api/jobs/{created['job_id']}",
                    headers={"X-Job-Token": created["job_token"], "X-RepoPilot-Token": "fixture-access"},
                )
                with urllib.request.urlopen(greq, timeout=5) as gresp:
                    job = json.loads(gresp.read().decode())
                if job["status"] == "failed":
                    break
                time.sleep(0.02)
            self.assertEqual(job["status"], "failed")
            self.assertIn("TimeoutError", job["error"])

            # 2. Quota exhaustion (max_daily_jobs=1) -> 429
            req2 = urllib.request.Request(
                f"http://127.0.0.1:{srv2.server_port}/api/jobs",
                data=json.dumps({"issue_url": "https://github.com/org/repo/issues/2"}).encode(),
                headers={"Content-Type": "application/json", "X-RepoPilot-Token": "fixture-access"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req2, timeout=5)
            self.assertEqual(ctx.exception.code, 429)
        finally:
            srv2.shutdown()
            srv2.server_close()

        # 3. Missing artifact on completed run raises FileNotFoundError
        job_id = "fedcba9876543210"
        class MissingArtOpener:
            def open(self, req, timeout=15):
                if "artifacts" in req.full_url:
                    return _FakeResp(json.dumps({"artifacts": []}).encode())
                return _FakeResp(
                    json.dumps({"workflow_runs": [{"id": 77, "status": "completed", "display_title": f"RepoPilot demo {job_id}"}]}).encode()
                )
        with self.assertRaises(FileNotFoundError):
            hf_app.poll_and_fetch_result(
                "o/r", job_id, github_token="tok", opener=MissingArtOpener(), deadline_seconds=5, poll_interval=0.01
            )

        # 4. Recursive redaction scrubs nested tokens
        from repopilot.security import redact_secrets_recursive
        scrubbed = redact_secrets_recursive({"nested": [{"err": "ghp_1234567890abcdef123456"}]})
        self.assertEqual(scrubbed["nested"][0]["err"], "[REDACTED_GITHUB_TOKEN]")


if __name__ == "__main__":
    unittest.main()
