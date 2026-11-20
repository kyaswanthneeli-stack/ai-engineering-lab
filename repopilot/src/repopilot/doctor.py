"""Read-only runtime preflight for RepoPilot's local verification workflow.

A preflight is not evidence that a proposed patch fixes an issue. External
model endpoints are deliberately never probed to avoid accidental data egress.
No credentials, endpoint URLs, or Docker stderr are included in diagnostics.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Provider redirect prohibited")


def inspect_runtime(*, live: bool = False, model: str | None = None,
                    base_url: str | None = None) -> dict:
    """Report reproducible prerequisites without executing repository code.

    The default mode makes no network requests or subprocess calls. --live
    checks Docker readiness and the model inventory of *local* Ollama only.
    It never probes remote model endpoints and never sends model prompts.
    """
    if not isinstance(live, bool):
        raise ValueError("live must be boolean")
    model = os.getenv("REPOPILOT_MODEL", "") if model is None else model
    base_url = os.getenv("REPOPILOT_BASE_URL", "") if base_url is None else base_url
    checks = []

    def record(name: str, status: str, message: str):
        checks.append({"name": name, "status": status, "message": message})

    record("python", "pass" if sys.version_info >= (3, 11) else "fail",
           "Requires Python 3.11 or newer")
    git = shutil.which("git") is not None
    docker = shutil.which("docker") is not None
    record("git", "pass" if git else "fail", "Git executable must be installed")
    record("docker_cli", "pass" if docker else "fail",
           "Docker CLI must be installed for sandbox verification")

    if not docker:
        record("docker_daemon", "fail", "Docker unavailable")
    elif not live:
        record("docker_daemon", "not_checked", "Use --live to test Docker daemon")
    else:
        try:
            completed = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True, text=True, timeout=5, check=False)
            up = completed.returncode == 0 and bool(completed.stdout.strip())
        except (OSError, subprocess.TimeoutExpired):
            up = False
        record("docker_daemon", "pass" if up else "fail",
               "Docker daemon reachable" if up else "Docker daemon unavailable")

    if not isinstance(model, str) or not model.strip() or len(model) > 120:
        record("model_config", "fail", "Set REPOPILOT_MODEL to a model identifier")
        model_ready = False
    else:
        record("model_config", "pass", "Model name configured")
        model_ready = True

    endpoint_ready = False
    local_ollama = False
    if not isinstance(base_url, str):
        valid = False
    else:
        try:
            parts = urllib.parse.urlsplit(base_url)
            valid = (parts.scheme in {"http", "https"} and bool(parts.hostname)
                     and not parts.username and not parts.password
                     and not parts.fragment and not parts.query)
            if parts.scheme == "http" and parts.hostname not in {
                    "localhost", "127.0.0.1", "::1"}:
                valid = False
            if valid:
                local_ollama = (
                    parts.scheme == "http" and
                    parts.hostname in {"localhost", "127.0.0.1", "::1"} and
                    parts.port == 11434 and
                    parts.path.rstrip("/") == "/v1")
        except (TypeError, ValueError):
            valid = False
    if not valid:
        record("provider_config", "fail",
               "Set REPOPILOT_BASE_URL to a valid local or HTTPS endpoint")
    else:
        endpoint_ready = True
        record("provider_config", "pass",
               "Configured model endpoint has an allowed scheme")

    if not (endpoint_ready and model_ready):
        record("model_available", "fail", "Model configuration incomplete")
    elif not live:
        record("model_available", "not_checked",
               "Use --live to check installed local Ollama models")
    elif not local_ollama:
        record("model_available", "not_checked",
               "External or nonstandard local provider is not probed")
    else:
        # Local *only*: localhost Ollama inventory, with a bounded response
        # and no redirects, credentials, source, or issue statements.
        available = False
        try:
            url = urllib.parse.urlunsplit((
                parts.scheme, parts.netloc, "/api/tags", "", ""))
            request = urllib.request.Request(url, method="GET")
            opener = urllib.request.build_opener(_NoRedirect())
            with opener.open(request, timeout=4) as response:
                payload = response.read(200_001)
            if len(payload) <= 200_000:
                data = json.loads(payload)
                if isinstance(data, dict) and isinstance(data.get("models"), list):
                    names = {m.get("name") for m in data["models"]
                             if isinstance(m, dict) and isinstance(m.get("name"), str)}
                    available = model in names
        except (OSError, TimeoutError, ValueError, TypeError):
            pass
        record("model_available", "pass" if available else "fail",
               "Configured model is installed locally" if available
               else "Local Ollama unavailable or configured model not installed")

    status = {c["name"]: c["status"] for c in checks}
    must_pass = ("python", "git", "docker_cli", "docker_daemon",
                 "model_config", "provider_config", "model_available")
    return {
        "mode": "live" if live else "offline",
        "checks": checks,
        "ready_for_verified_workflow": all(status[key] == "pass" for key in must_pass),
        "note": ("Preflight checks tools and local provider availability only; "
                 "it does not run, review, or score a model-generated patch."),
    }
