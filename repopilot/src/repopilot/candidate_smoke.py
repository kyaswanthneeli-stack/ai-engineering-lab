"""Bounded, comparative candidate smoke check in a locked-down Docker runner.

This never executes an untrusted repository or issue snippet on the host.
A smoke pass is NOT a SWE-bench resolution. Only a before-pass/after-fail
transition can reject a candidate; unavailable dependencies are inconclusive.
"""
from __future__ import annotations

import ast
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from .patches import apply_patch
from .pr import patch_targets

# Keep patch paths predictable when embedding them in Docker --mount values.
_SAFE_PATH = re.compile(r"[A-Za-z0-9_./-]{1,240}\Z")
_FENCE = re.compile(r"```(?:python|py)\s*\n(.*?)\n```", re.I | re.S)
_IMAGE = "python:3.12-alpine"


def _reproducer(issue: str, targets: list[str]) -> tuple[str, str]:
    """Use a small, parseable public issue snippet or import the target.

    Tests can also exercise this with explicit assertion snippets; no
    untrusted issue text gets evaluated in the host Python interpreter.
    """
    for match in _FENCE.finditer(issue[:12000]):
        code = match.group(1).strip()
        if not 20 <= len(code) <= 1700:
            continue
        try:
            ast.parse(code)
        except SyntaxError:
            continue
        return code + "\n", "issue_python_example"
    # Import is a weak smoke; both sides passing is not proof of correctness.
    names = []
    for path in targets[:2]:
        module = path[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        if module and all(part.isidentifier() for part in module.split(".")):
            names.append(module)
    if not names:
        return "", "none"
    return ("import importlib\n" + "".join(
        "importlib.import_module(" + repr(name) + ")\n" for name in names),
        "module_import")


def _run_docker(repo: Path, script: str, *, overlay: Path | None,
                targets: list[str], timeout: float) -> tuple[int | None, bool]:
    """Run a fixed Python command with no host credentials, network or writes."""
    container = "repopilot-smoke-" + uuid.uuid4().hex[:16]
    args = [
        "docker", "run", "--name", container, "--rm", "--pull=never",
        "--network=none", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=64",
        "--memory=512m", "--cpus=1", "--read-only",
        "--tmpfs=/tmp:rw,nosuid,nodev,size=32m,mode=1777",
        "--user=65534:65534", "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "PYTHONPATH=/workspace",
        "-v", str(repo) + ":/workspace:ro",
    ]
    if overlay is not None:
        for path in targets:
            args.extend(["--mount", "type=bind,src=" +
                         str(overlay / path) + ",dst=/workspace/" +
                         path + ",readonly"])
    args.extend(["-w", "/workspace", _IMAGE, "python", "-c", script])
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, check=False,
            timeout=timeout)
        # Do not retain untrusted source, traceback or issue contents.
        return result.returncode, False
    except subprocess.TimeoutExpired:
        try:
            cleanup = subprocess.run(
                ["docker", "rm", "-f", container],
                capture_output=True, timeout=6, check=False)
            return None, cleanup.returncode != 0
        except (OSError, subprocess.TimeoutExpired):
            return None, True
    except OSError:
        return None, False


def smoke_candidate(repo: Path, patch: str, issue: str, *,
                    timeout: int = 18) -> dict:
    """Return a conservative, bounded and serializable validation report.

    A clear regression is defined narrowly: the exact same Python probe
    exits 0 on original source and nonzero on the candidate overlay.
    Timeouts, missing Docker/image/dependencies, original failures, and
    absent useful tests are all non-blocking and NEVER counted as passing.
    """
    if not 8 <= timeout <= 30:
        raise ValueError("Candidate smoke timeout must be 8–30 seconds")
    started = time.monotonic()
    result = {"status": "inconclusive", "probe": "none"}
    if shutil.which("docker") is None:
        return {"status": "skipped", "reason": "docker_unavailable"}
    root = repo.resolve(strict=True)
    targets = patch_targets(patch)
    if not 1 <= len(targets) <= 4:
        return {"status": "skipped", "reason": "too_many_patch_targets"}
    for name in targets:
        source = root / name
        if (not _SAFE_PATH.fullmatch(name) or
                ".." in Path(name).parts or
                not source.is_file() or
                not source.resolve().is_relative_to(root) or
                any((root / Path(*Path(name).parts[:n])).is_symlink()
                    for n in range(1, len(Path(name).parts) + 1)) or
                source.stat().st_size > 100_000):
            return {"status": "skipped", "reason": "unsafe_or_large_patch_target"}
    script, kind = _reproducer(issue, targets)
    if not script:
        return {"status": "skipped", "reason": "no_probe"}
    result["probe"] = kind
    with tempfile.TemporaryDirectory(prefix="repopilot-candidate-") as tmp:
        staging = Path(tmp) / "overlay"
        staging.mkdir()
        for name in targets:
            dest = staging / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, dest)
        # Git applies only data to a private temporary copy, never source
        # in the original pinned checkout.
        try:
            apply_patch(staging, patch)
        except (ValueError, OSError, subprocess.TimeoutExpired):
            return {"status": "inconclusive", "probe": kind,
                    "reason": "candidate_overlay_unavailable"}
        remaining = timeout - (time.monotonic() - started)
        if remaining < 8:
            return {"status": "skipped", "probe": kind,
                    "reason": "deadline"}
        before, unsafe_cleanup = _run_docker(
            root, script, overlay=None, targets=targets,
            timeout=min(7, remaining / 2))
        if unsafe_cleanup:
            return {"status": "inconclusive", "probe": kind,
                    "reason": "container_cleanup_unconfirmed"}
        if before is None:
            return {"status": "inconclusive", "probe": kind,
                    "reason": "baseline_unavailable"}
        if before != 0:
            # Could be an expected reproduction failure or missing imports.
            # Never silently classify a baseline failure as a patch failure.
            return {"status": "inconclusive", "probe": kind,
                    "reason": "baseline_did_not_pass"}
        remaining = timeout - (time.monotonic() - started)
        if remaining < 3:
            return {"status": "skipped", "probe": kind, "reason": "deadline"}
        after, unsafe_cleanup = _run_docker(
            root, script, overlay=staging, targets=targets,
            timeout=min(7, remaining))
        if unsafe_cleanup or after is None:
            return {"status": "inconclusive", "probe": kind,
                    "reason": "candidate_or_cleanup_unavailable"}
        if after != 0:
            return {"status": "regression", "probe": kind,
                    "reason": "baseline_passed_candidate_failed"}
        return {"status": "no_regression_observed", "probe": kind,
                "reason": "limited_probe_only"}
