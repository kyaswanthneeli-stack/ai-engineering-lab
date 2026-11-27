"""Hugging Face Spaces public web backend for RepoPilot (remote-only, zero local code exec)."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from collections import OrderedDict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

_REPO_SRC = Path(__file__).resolve().parents[1] / "src"
if _REPO_SRC.exists() and str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

from repopilot.inference_resilience import build_safe_opener
from repopilot.security import redact_secrets, redact_secrets_recursive

_ISSUE_URL_RE = re.compile(
    r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/([1-9][0-9]{0,7})/?$"
)
_JOB_ID_RE = re.compile(r"^[a-f0-9]{16}$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_STATIC_DIR = Path(__file__).resolve().parent / "static"

RUNNER_REPO = "kyaswanthneeli-stack/ai-engineering-lab"
DEMO_TARGET = (*RUNNER_REPO.split("/"), 1)
WORKFLOW = "repopilot-remote-issue-agent.yml"
MODEL = "qwen2.5-coder:3b"


def parse_github_issue_url(url: str) -> tuple[str, str, int]:
    """Validate and parse a public GitHub issue URL."""
    if not isinstance(url, str) or len(url) > 250:
        raise ValueError("Issue URL must be a string <= 250 characters")
    match = _ISSUE_URL_RE.match(url.strip())
    if not match:
        raise ValueError("Invalid GitHub issue URL (expected https://github.com/owner/repo/issues/123)")
    owner, repo, num_str = match.group(1), match.group(2), match.group(3)
    if owner in (".", "..") or repo in (".", ".."):
        raise ValueError("Invalid repository owner or name")
    return owner, repo, int(num_str)


class RateLimiter:
    """Thread-safe per-IP sliding-window rate limiter."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 600) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, now: float | None = None) -> tuple[bool, int]:
        ts = time.monotonic() if now is None else now
        cutoff = ts - self.window_seconds
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.max_requests:
                retry_after = max(1, int(q[0] + self.window_seconds - ts))
                return False, retry_after
            q.append(ts)
            return True, 0


class PersistentDailyQuota:
    """File-backed daily global execution quota that fails closed on storage errors."""

    def __init__(self, state_path: Path, max_daily_jobs: int = 50) -> None:
        self.state_path = state_path
        self.max_daily_jobs = max_daily_jobs
        self._lock = threading.Lock()

    def consume(self, *, now: float | None = None) -> tuple[bool, int]:
        today = int((time.time() if now is None else now) // 86400)
        with self._lock:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path = self.state_path.with_suffix(".lock")
            with open(lock_path, "a+", encoding="utf-8") as lock_fp:
                fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX)
                try:
                    data = {"day": today, "count": 0}
                    if self.state_path.exists():
                        loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
                        if not isinstance(loaded, dict) or "day" not in loaded or "count" not in loaded:
                            raise ValueError("Corrupt quota state")
                        if int(loaded["day"]) == today:
                            data["count"] = int(loaded["count"])
                    if data["count"] >= self.max_daily_jobs:
                        return False, 0
                    data["count"] += 1
                    tmp = self.state_path.with_suffix(".tmp")
                    tmp.write_text(json.dumps(data), encoding="utf-8")
                    os.replace(tmp, self.state_path)
                    return True, self.max_daily_jobs - data["count"]
                finally:
                    fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)


class JobStore:
    """Thread-safe bounded FIFO store with per-job authorization secrets."""

    def __init__(self, max_jobs: int = 100) -> None:
        self.max_jobs = max_jobs
        self._jobs: OrderedDict[str, dict] = OrderedDict()
        self._secrets: dict[str, str] = {}
        self._lock = threading.Lock()

    def create(self, issue_url: str, owner: str, repo: str, issue_number: int) -> tuple[dict, str]:
        job_id = uuid.uuid4().hex[:16]
        job_secret = secrets.token_urlsafe(24)
        record = {
            "job_id": job_id,
            "issue_url": issue_url,
            "repo": f"{owner}/{repo}",
            "issue_number": issue_number,
            "base_sha": "",
            "status": "queued",
            "progress": 5,
            "stage": "queued",
            "issue_title": "",
            "patch": "",
            "outcome": "",
            "failed_stage": "",
            "before_tests": {"status": "not_run", "summary": "Awaiting remote GitHub Actions verification"},
            "after_tests": {"status": "not_run", "summary": "Awaiting remote GitHub Actions verification"},
            "verification_mode": "remote_github_actions_only",
            "workflow_dispatched": False,
            "workflow_run_id": None,
            "workflow_url": "",
            "error": "",
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        with self._lock:
            self._jobs[job_id] = record
            self._secrets[job_id] = job_secret
            while len(self._jobs) > self.max_jobs:
                evicted_id, _ = self._jobs.popitem(last=False)
                self._secrets.pop(evicted_id, None)
        return dict(record), job_secret

    def authorize(self, job_id: str, provided_secret: str) -> bool:
        with self._lock:
            expected = self._secrets.get(job_id)
        if not expected or not provided_secret:
            return False
        return hmac.compare_digest(provided_secret.encode("utf-8"), expected.encode("utf-8"))

    def update(self, job_id: str, **fields) -> dict | None:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return None
            for k, v in fields.items():
                rec[k] = redact_secrets_recursive(v)
            rec["updated_at"] = int(time.time())
            return dict(rec)

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            rec = self._jobs.get(job_id)
            return dict(rec) if rec is not None else None


def verify_access_token(headers, expected_token: str | None = None) -> bool:
    """Check X-RepoPilot-Token or Bearer token when REPOPILOT_ACCESS_TOKEN is set."""
    expected = expected_token if expected_token is not None else os.getenv("REPOPILOT_ACCESS_TOKEN", "")
    if not expected:
        return False
    provided = headers.get("X-RepoPilot-Token", "")
    if not provided:
        auth = headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            provided = auth[7:].strip()
    return bool(provided) and hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def resolve_issue_and_base_sha(
    owner: str,
    repo: str,
    number: int,
    *,
    github_token: str | None = None,
    opener=None,
) -> tuple[str, str]:
    """Fetch public issue title (rejecting PRs) and immutable default-branch HEAD SHA."""
    client = opener or build_safe_opener()
    token = github_token if github_token is not None else os.getenv("GITHUB_TOKEN", "")
    base_headers = {"Accept": "application/vnd.github+json", "User-Agent": "RepoPilot-Space/2.3"}
    if token:
        base_headers["Authorization"] = f"Bearer {token}"

    issue_req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/issues/{number}",
        headers=base_headers,
        method="GET",
    )
    with client.open(issue_req, timeout=12) as resp:
        issue_raw = resp.read(150_001)
    if len(issue_raw) > 150_000:
        raise ValueError("Issue payload exceeded 150 KB")
    issue_data = json.loads(issue_raw.decode("utf-8"))
    if "pull_request" in issue_data:
        raise ValueError("Target URL is a Pull Request, not an Issue")
    title = redact_secrets(str(issue_data.get("title") or "")[:200])

    repo_req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=base_headers,
        method="GET",
    )
    with client.open(repo_req, timeout=12) as resp:
        repo_data = json.loads(resp.read(100_000).decode("utf-8"))
    branch = str(repo_data.get("default_branch") or "main")

    ref_req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{branch}",
        headers=base_headers,
        method="GET",
    )
    with client.open(ref_req, timeout=12) as resp:
        ref_data = json.loads(resp.read(50_000).decode("utf-8"))
    sha = str(ref_data["object"]["sha"])
    if not _SHA_RE.match(sha):
        raise ValueError(f"Invalid commit SHA resolved: {sha!r}")
    return title, sha


def dispatch_remote_verification(
    owner: str,
    repo: str,
    number: int,
    base_sha: str,
    job_id: str,
    *,
    github_token: str | None = None,
    opener=None,
) -> tuple[bool, str]:
    """Dispatch GitHub Actions workflow with target_repo, issue_number, base_sha, and job_id."""
    token = github_token if github_token is not None else os.getenv("GITHUB_TOKEN", "")
    if (owner, repo, number) != DEMO_TARGET or not _SHA_RE.fullmatch(base_sha) or not _JOB_ID_RE.fullmatch(job_id):
        raise ValueError("The hosted demo only runs the calculator fixture")
    runner_repo = RUNNER_REPO
    workflow = WORKFLOW
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required to dispatch remote GitHub Actions verification")

    url = f"https://api.github.com/repos/{runner_repo}/actions/workflows/{workflow}/dispatches"
    body = json.dumps({
        "ref": "main",
        "inputs": {
            "target_repo": f"{owner}/{repo}",
            "issue_number": str(number),
            "base_sha": base_sha,
            "job_id": job_id,
        },
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "RepoPilot-Space/2.3",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    client = opener or build_safe_opener()
    with client.open(req, timeout=15) as resp:
        if resp.status in (200, 201, 204):
            return True, f"https://github.com/{runner_repo}/actions/workflows/{workflow}"
    raise RuntimeError("GitHub Actions dispatch failed")


class _ArtifactRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        host = parsed.hostname or ""
        if (parsed.scheme != "https" or parsed.username or parsed.password
                or not host.endswith((".blob.core.windows.net", ".githubusercontent.com"))):
            raise ValueError("Unexpected artifact download destination")
        redirect = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirect is not None:
            redirect.remove_header("Authorization")
        return redirect


def poll_and_fetch_result(
    runner_repo: str,
    job_id: str,
    *,
    target_repo: str = "",
    base_sha: str = "",
    github_token: str,
    opener=None,
    artifact_opener=None,
    deadline_seconds: int = 600,
    poll_interval: float = 5.0,
    on_progress: Callable[[str, int], None] | None = None,
) -> dict:
    """Poll GitHub Actions for the matching run, download artifact ZIP, and return verified JSON."""
    client = opener or build_safe_opener()
    dl_client = artifact_opener or urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _ArtifactRedirect()
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "User-Agent": "RepoPilot-Space/2.3",
    }
    artifact_name = f"repopilot-result-{job_id}"
    end_time = time.monotonic() + deadline_seconds
    matched_run: dict | None = None

    while time.monotonic() < end_time:
        runs_req = urllib.request.Request(
            f"https://api.github.com/repos/{runner_repo}/actions/workflows/{WORKFLOW}/runs?event=workflow_dispatch&per_page=15",
            headers=headers,
            method="GET",
        )
        with client.open(runs_req, timeout=15) as resp:
            runs_data = json.loads(resp.read(500_000).decode("utf-8"))

        for run in runs_data.get("workflow_runs", []):
            run_id = run.get("id")
            if not isinstance(run_id, int) or run.get("display_title") != f"RepoPilot demo {job_id}":
                continue
            arts_req = urllib.request.Request(
                f"https://api.github.com/repos/{runner_repo}/actions/runs/{run_id}/artifacts",
                headers=headers,
                method="GET",
            )
            with client.open(arts_req, timeout=15) as aresp:
                arts_data = json.loads(aresp.read(200_000).decode("utf-8"))
            matching = [a for a in arts_data.get("artifacts", []) if a.get("name") == artifact_name]
            if run.get("status") == "completed":
                if not matching:
                    # Only raise if this run had our job_id in its display title/name
                    if job_id in str(run.get("display_title") or "") or job_id in str(run.get("name") or ""):
                        raise FileNotFoundError(f"Run {run_id} completed without artifact {artifact_name}")
                    continue
                matched_run = run
                artifact_id = matching[0].get("id")
                if not isinstance(artifact_id, int):
                    raise ValueError("Invalid artifact id")
                dl_url = f"https://api.github.com/repos/{runner_repo}/actions/artifacts/{artifact_id}/zip"
                dl_req = urllib.request.Request(dl_url, headers=headers, method="GET")
                with dl_client.open(dl_req, timeout=30) as zresp:
                    zip_bytes = zresp.read(2_000_001)
                if len(zip_bytes) > 2_000_000:
                    raise ValueError("Verification artifact exceeded 2 MB cap")
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                    target_name = f"repopilot-result-{job_id}.json"
                    if target_name not in zf.namelist():
                        raise ValueError(f"Missing {target_name} inside artifact archive")
                    info = zf.getinfo(target_name)
                    if info.file_size > 500_000:
                        raise ValueError("Uncompressed result exceeded size cap")
                    payload = json.loads(zf.read(info).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("Expected an object in verification artifact")
                if payload.get("job_id") != job_id:
                    raise ValueError("Artifact job_id mismatch")
                if target_repo and payload.get("target_repo") != target_repo:
                    raise ValueError("Artifact target_repo mismatch")
                if base_sha and payload.get("base_sha") != base_sha:
                    raise ValueError("Artifact base_sha mismatch")
                patch_txt = str(payload.get("patch") or "")
                expected_sha = str(payload.get("patch_sha256") or "")
                if hashlib.sha256(patch_txt.encode("utf-8")).hexdigest() != expected_sha:
                    raise ValueError("Artifact patch_sha256 integrity mismatch")
                if payload.get("outcome") == "verified_in_sandbox" and (
                        run.get("conclusion") != "success"
                        or payload.get("model_generated_proposal") is not True
                        or payload.get("baseline", {}).get("exit_code") != 0
                        or payload.get("before_tests", {}).get("exit_code") != 1
                        or payload.get("after_tests", {}).get("exit_code") != 0
                        or not patch_txt):
                    raise ValueError("Artifact could not establish a verified model repair")
                payload["workflow_run_id"] = run_id
                payload["workflow_url"] = str(run.get("html_url") or "")
                return redact_secrets_recursive(payload)
            if run.get("status") in ("queued", "in_progress") and on_progress:
                on_progress(f"github_actions_{run.get('status')}", 75)

        if matched_run is None and time.monotonic() + poll_interval < end_time:
            time.sleep(poll_interval)
        else:
            break

    raise TimeoutError(f"Timed out waiting for remote verification artifact {artifact_name}")


def format_markdown_report(job: dict) -> str:
    """Render a sanitized downloadable Markdown engineering report."""
    return redact_secrets(
        f"# RepoPilot Remote Engineering Report\n\n"
        f"- **Job ID:** `{job['job_id']}`\n"
        f"- **Repository:** `{job['repo']}`\n"
        f"- **Base SHA:** `{job.get('base_sha') or 'N/A'}`\n"
        f"- **Issue:** {job['issue_url']}\n"
        f"- **Issue Title:** {job.get('issue_title') or 'N/A'}\n"
        f"- **Status:** `{job['status']}` (`{job['stage']}`)\n"
        f"- **Outcome:** `{job.get('outcome') or 'N/A'}`\n"
        f"- **Workflow URL:** {job.get('workflow_url') or 'N/A'}\n\n"
        f"## Before / After Verification\n"
        f"- **Before:** `{job['before_tests'].get('status')}` — {job['before_tests'].get('summary')}\n"
        f"- **After:** `{job['after_tests'].get('status')}` — {job['after_tests'].get('summary')}\n\n"
        f"## Independently Verified Patch\n"
        f"```diff\n{job.get('patch') or '# No verified patch produced'}\n```\n"
        + (f"\n## Diagnostics\n- {job['error']}\n" if job.get("error") else "")
    )


def make_handler(
    store: JobStore,
    limiter: RateLimiter,
    quota: PersistentDailyQuota,
    *,
    max_concurrent_jobs: int = 3,
    allowed_target: tuple[str, str, int] | None = DEMO_TARGET,
    issue_resolver: Callable = resolve_issue_and_base_sha,
    verifier_dispatcher: Callable = dispatch_remote_verification,
    result_poller: Callable = poll_and_fetch_result,
):
    """Build HTTP request handler with bounded concurrency and per-job authorization."""
    concurrency_sem = threading.BoundedSemaphore(value=max_concurrent_jobs)

    class RepoPilotHandler(BaseHTTPRequestHandler):
        server_version = "RepoPilotSpace/2.3"

        def log_message(self, format, *args) -> None:  # noqa: A002
            return

        def _send_security_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'",
            )

        def _send_json(self, code: int, payload: dict, extra_headers: dict | None = None) -> None:
            body = json.dumps(redact_secrets_recursive(payload)).encode("utf-8")
            self.send_response(code)
            self._send_security_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _client_ip(self) -> str:
            # Never trust X-Forwarded-For unless explicitly enabled behind a trusted proxy
            if os.getenv("REPOPILOT_TRUST_PROXY") == "1" and self.client_address[0] in ("127.0.0.1", "::1"):
                forwarded = self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                if forwarded:
                    return forwarded
            return self.client_address[0]

        def _authorize_job(self, job_id: str) -> bool:
            if not verify_access_token(self.headers):
                return False
            job_tok = self.headers.get("X-Job-Token", "")
            return store.authorize(job_id, job_tok)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            if path in ("/", "/index.html"):
                content = (_STATIC_DIR / "index.html").read_bytes()
                self.send_response(200)
                self._send_security_headers()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

            if path == "/health":
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "model": MODEL,
                        "github_actions_configured": bool(os.getenv("GITHUB_TOKEN")),
                        "auth_required": bool(os.getenv("REPOPILOT_ACCESS_TOKEN")),
                        "sandbox_mode": "remote_only_no_local_exec",
                    },
                )
                return

            if path.startswith("/api/jobs/"):
                parts = path.strip("/").split("/")
                if len(parts) not in (3, 4) or not _JOB_ID_RE.match(parts[2]):
                    self._send_json(404, {"error": "Job not found"})
                    return
                job_id = parts[2]
                qs = parse_qs(parsed.query)
                if not self._authorize_job(job_id):
                    self._send_json(403, {"error": "Valid access and X-Job-Token required"})
                    return
                job = store.get(job_id)
                if job is None:
                    self._send_json(404, {"error": "Job not found"})
                    return
                if len(parts) == 4 and parts[3] == "report":
                    fmt = qs.get("format", ["md"])[0]
                    if fmt == "json":
                        self._send_json(
                            200,
                            job,
                            {"Content-Disposition": f'attachment; filename="repopilot-{job_id}.json"'},
                        )
                        return
                    md = format_markdown_report(job).encode("utf-8")
                    self.send_response(200)
                    self._send_security_headers()
                    self.send_header("Content-Type", "text/markdown; charset=utf-8")
                    self.send_header("Content-Disposition", f'attachment; filename="repopilot-{job_id}.md"')
                    self.send_header("Content-Length", str(len(md)))
                    self.end_headers()
                    self.wfile.write(md)
                    return
                if len(parts) == 3:
                    self._send_json(200, job)
                    return

            self._send_json(404, {"error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/jobs":
                self._send_json(404, {"error": "Not found"})
                return
            if not verify_access_token(self.headers):
                self._send_json(401, {"error": "Valid X-RepoPilot-Token required"})
                return
            allowed, retry_after = limiter.allow(self._client_ip())
            if not allowed:
                self._send_json(
                    429,
                    {"error": f"Rate limit exceeded; retry after {retry_after}s"},
                    {"Retry-After": str(retry_after)},
                )
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= 8192:
                    raise ValueError("Request body must be 1..8192 bytes")
                self.connection.settimeout(10)
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(body, dict):
                    raise ValueError("Expected a JSON object")
                owner, repo, number = parse_github_issue_url(body.get("issue_url", ""))
            except (ValueError, OSError, RecursionError):
                self._send_json(400, {"error": "Invalid issue request"})
                return

            if allowed_target is not None and (owner, repo, number) != allowed_target:
                self._send_json(403, {"error": "Use the calculator fixture linked above"})
                return
            if not concurrency_sem.acquire(blocking=False):
                self._send_json(503, {"error": "Server at max concurrent job capacity; retry shortly"})
                return
            try:
                ok_quota, _ = quota.consume()
            except (OSError, ValueError, TypeError):
                concurrency_sem.release()
                self._send_json(503, {"error": "Persistent quota storage unavailable; failing closed"})
                return
            if not ok_quota:
                concurrency_sem.release()
                self._send_json(429, {"error": "Daily global execution quota reached"})
                return

            job, job_secret = store.create(f"https://github.com/{owner}/{repo}/issues/{number}", owner, repo, number)
            job_id = job["job_id"]

            def _worker() -> None:
                try:
                    store.update(job_id, status="running", stage="resolving_base_sha", progress=15)
                    title, base_sha = issue_resolver(owner, repo, number)
                    store.update(job_id, issue_title=title, base_sha=base_sha, stage="dispatching_github_actions", progress=35)

                    dispatched, workflow_url = verifier_dispatcher(owner, repo, number, base_sha, job_id)
                    store.update(
                        job_id,
                        status="verifying",
                        stage="polling_github_actions",
                        progress=55,
                        workflow_dispatched=dispatched,
                        workflow_url=workflow_url,
                    )

                    runner_repo = RUNNER_REPO
                    token = os.getenv("GITHUB_TOKEN", "")
                    verified = result_poller(
                        runner_repo,
                        job_id,
                        target_repo=f"{owner}/{repo}",
                        base_sha=base_sha,
                        github_token=token,
                        deadline_seconds=int(os.getenv("REPOPILOT_JOB_DEADLINE_SECONDS", "600")),
                        on_progress=lambda st, pct: store.update(job_id, stage=st, progress=pct),
                    )
                    outcome = str(verified.get("outcome") or "")
                    before = verified.get("before_tests") or {}
                    after = verified.get("after_tests") or {}
                    final_status = "completed" if outcome == "verified_in_sandbox" else "failed"
                    store.update(
                        job_id,
                        status=final_status,
                        stage=outcome or "verification_finished",
                        progress=100,
                        outcome=outcome,
                        failed_stage=str(verified.get("failed_stage") or ""),
                        patch=str(verified.get("patch") or ""),
                        workflow_run_id=verified.get("workflow_run_id"),
                        workflow_url=str(verified.get("workflow_url") or workflow_url),
                        before_tests={
                            "status": f"exit_{before.get('exit_code')}",
                            "summary": redact_secrets(str(before.get("output") or ""))[:600],
                        },
                        after_tests={
                            "status": f"exit_{after.get('exit_code')}",
                            "summary": redact_secrets(str(after.get("output") or ""))[:600],
                        },
                    )
                except Exception as exc:
                    store.update(
                        job_id,
                        status="failed",
                        stage="error",
                        progress=100,
                        error=f"Remote verification failed ({type(exc).__name__})",
                    )
                finally:
                    concurrency_sem.release()

            threading.Thread(target=_worker, daemon=True).start()
            response_payload = dict(job)
            response_payload["job_token"] = job_secret
            self._send_json(202, response_payload)

    return RepoPilotHandler


def main() -> None:
    port = int(os.getenv("PORT", "7860"))
    store = JobStore(max_jobs=100)
    limiter = RateLimiter(
        max_requests=int(os.getenv("REPOPILOT_RATE_LIMIT_MAX", "5")),
        window_seconds=int(os.getenv("REPOPILOT_RATE_LIMIT_WINDOW", "600")),
    )
    quota = PersistentDailyQuota(
        state_path=Path(os.getenv("REPOPILOT_QUOTA_PATH", "/tmp/repopilot_quota.json")),
        max_daily_jobs=int(os.getenv("REPOPILOT_DAILY_QUOTA", "50")),
    )
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(store, limiter, quota))
    server.serve_forever()


if __name__ == "__main__":
    main()
