"""Bounded, comparative candidate smoke check in a locked-down Docker runner.

This never executes an untrusted repository or issue snippet on the host.
A smoke pass is NOT a SWE-bench resolution. Only a before-pass/after-fail
transition can reject a candidate; unavailable dependencies are inconclusive.
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from .patches import apply_patch
from .pr import patch_targets
from .source_examples import select_source_examples, runner_script
from . import native_runtime

# Keep patch paths predictable when embedding them in Docker --mount values.
_SAFE_PATH = re.compile(r"[A-Za-z0-9_./-]{1,240}\Z")
_FENCE = re.compile(r"```(?:python|py)\s*\n(.*?)\n```", re.I | re.S)
_IMAGE = "python:3.12-alpine"
_TRUSTED_OFFLINE_DEPS_IMAGE = "repopilot-candidate-deps:py310"
_APPROVED_IMAGES = frozenset({_IMAGE, _TRUSTED_OFFLINE_DEPS_IMAGE})


def _bootstrap(targets: list[str]) -> tuple[str, str]:
    """Opt-in, developer-owned import setup, executed only inside Docker.

    No target setup.py, migrations, app configuration or package install is
    accepted from a model. Both original and candidate use this exact prefix.
    These weak import profiles are not official SWE-bench environments.
    """
    if os.getenv("REPOPILOT_CANDIDATE_SMOKE_BOOTSTRAP", "0").strip() != "1":
        return "", "none"
    if any(name.startswith("sympy/") for name in targets):
        return ("import collections, collections.abc\n"
                "for _name in ('Mapping','MutableMapping','Iterable','Callable','Sequence','MutableSet','Set','Hashable','Iterator'):\n"
                "    if not hasattr(collections, _name):\n"
                "        setattr(collections, _name, getattr(collections.abc, _name))\n",
                "legacy_collections_import_setup")
    if any(name.startswith("django/") for name in targets):
        return ("from django.conf import settings\n"
                "if not settings.configured:\n"
                "    settings.configure(INSTALLED_APPS=['django.contrib.contenttypes'], "
                "DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}, "
                "SECRET_KEY='repopilot-offline-smoke-fixture')\n"
                "import django\ndjango.setup()\n", "django_minimal_import_setup")
    return "", "source_layout_import_setup"


def _approved_image() -> str | None:
    """Images are selected only by trusted operator environment, never by issue.

    No docker pull is allowed during candidate verification; the optional
    dependency-rich image must have been prebuilt by the CI workflow.
    """
    image = os.getenv("REPOPILOT_CANDIDATE_SMOKE_IMAGE", _IMAGE).strip()
    return image if image in _APPROVED_IMAGES else None



def _reproducer(issue: str, targets: list[str], *, root: Path | None = None,
                evidence: dict | None = None) -> tuple[str, str]:
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
    if (root is not None and
            os.getenv("REPOPILOT_CANDIDATE_SOURCE_EXAMPLES", "0").strip() == "1"):
        selection = select_source_examples(root, targets)
        if selection is not None:
            if evidence is not None:
                evidence["source_examples"] = {k: v for k, v in selection.items() if k != "text"}
            script, _ = _import_probe([selection["path"]], root=root)
            return script + runner_script(selection), "source_doctest"
    return _import_probe(targets, root=root)


def _import_probe(targets: list[str], *, root: Path | None = None) -> tuple[str, str]:
    # Import is a weak smoke; both sides passing is not proof of correctness.
    names = []
    origins = []
    for original_path in targets[:2]:
        path = original_path
        if ((os.getenv("REPOPILOT_CANDIDATE_SMOKE_BOOTSTRAP", "0").strip() == "1"
                or native_runtime.selected(targets))
                and root is not None and path.startswith(("src/", "lib/"))
                and not (root / path.split("/", 1)[0] / "__init__.py").exists()):
            path = path.split("/", 1)[1]
        module = path[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        if module and all(part.isidentifier() for part in module.split(".")):
            names.append(module)
            origins.append("/workspace/" + original_path)
    if not names:
        return "", "none"
    return ("import importlib\nfrom pathlib import Path\n" + "".join(
        "_module = importlib.import_module(" + repr(name) + ")\n"
        "assert Path(_module.__file__).resolve() == Path(" + repr(origin) + ").resolve(), 'unexpected_source_origin'\n"
        for name, origin in zip(names, origins)),
        "module_import")


def _failure_category(code: int, stderr_tail: str) -> str | None:
    """Best-effort observed category, never retain exception text or paths.

    Untrusted code can spoof stderr. Categories are diagnostic hints only;
    they never turn a failing baseline into a pass or establish root cause.
    """
    if code == 0:
        return None
    if code in (125, 126, 127):
        return "container_runtime_error"
    if code < 0 or code >= 128:
        return "resource_or_signal_exit"
    lines = stderr_tail[-4096:].splitlines()
    last = next((line for line in reversed(lines) if line.strip()), "")
    exception = last.split(":", 1)[0].strip()
    if exception in {"ImportError", "AttributeError"} and re.search(
            r"(?:cannot import name|has no attribute) ['\"](?:Mapping|MutableMapping|Iterable|Callable|Sequence|MutableSet|Set|Hashable|Iterator)['\"]", last
    ) and ("from 'collections'" in last or "module 'collections'" in last):
        return "legacy_collections_api"
    if exception in {"ImportError", "ModuleNotFoundError"} and re.search(
            r"(?:matplotlib\.(?:_c_internal_utils|_path)|cannot import name ['\"](?:_c_internal_utils|_path)['\"])", last):
        return "native_extension_unavailable"
    return {
        "ModuleNotFoundError": "import_error",
        "ImportError": "import_error",
        "django.core.exceptions.ImproperlyConfigured": "configuration_error",
        "ImproperlyConfigured": "configuration_error",
        "SyntaxError": "syntax_error",
        "IndentationError": "syntax_error",
        "TabError": "syntax_error",
        "AssertionError": "assertion_failed",
        "PermissionError": "permission_error",
        "FileNotFoundError": "file_not_found",
    }.get(exception, "nonzero_exit")


def _run_docker(repo: Path, script: str, *, overlay: Path | None,
                targets: list[str], timeout: float,
                diagnostics: dict | None = None,
                phase: str = "baseline") -> tuple[int | None, bool]:
    """Run a fixed Python command with no host credentials, network or writes."""
    container = "repopilot-smoke-" + uuid.uuid4().hex[:16]
    if phase not in {"baseline", "fallback_baseline", "behavior_baseline", "candidate"}:
        raise ValueError("Invalid smoke phase")
    def record(code, category):
        if diagnostics is not None:
            diagnostics[phase + "_exit_code"] = code
            diagnostics[phase + "_failure_category"] = category
    def cleanup_failed():
        try:
            cleanup = subprocess.run(
                ["docker", "rm", "-f", container],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=6, check=False)
            return cleanup.returncode != 0
        except (OSError, subprocess.TimeoutExpired):
            return True
    args = [
        "docker", "run", "--name", container, "--rm", "--pull=never",
        "--network=none", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=64",
        "--memory=512m", "--cpus=1", "--read-only",
        "--tmpfs=/tmp:rw,nosuid,nodev,size=32m,mode=1777",
        "--user=65534:65534", "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", ("PYTHONPATH=/workspace:/workspace/src:/workspace/lib"
               if os.getenv("REPOPILOT_CANDIDATE_SMOKE_BOOTSTRAP", "0").strip() == "1"
               else "PYTHONPATH=/workspace"),
        "-v", str(repo) + ":/workspace:ro",
    ]
    use_native = native_runtime.selected(targets)
    if use_native:
        args.extend(["-e", "MPLCONFIGDIR=/tmp/mpl-config", "-e", "MPLBACKEND=Agg",
                     "-e", "MATPLOTLIBRC=/testbed/lib/matplotlib/mpl-data",
                     "-e", "OPENBLAS_NUM_THREADS=1", "-e", "OMP_NUM_THREADS=1",
                     "--entrypoint", native_runtime.NATIVE_PYTHON])
        script = native_runtime.prefix(repo, targets) + script
    if diagnostics is not None:
        diagnostics[phase + "_runtime_profile"] = "matplotlib_native_pinned" if use_native else "generic_python"
    if overlay is not None:
        for path in targets:
            args.extend(["--mount", "type=bind,src=" +
                         str(overlay / path) + ",dst=/workspace/" +
                         path + ",readonly"])
    image = _approved_image()
    if image is None:
        raise ValueError("Unapproved candidate smoke runtime image")
    if use_native:
        image = native_runtime.MATPLOTLIB_IMAGE
    args.extend(["-w", "/workspace", image])
    if not use_native:
        args.append("python")
    args.extend(["-c", script])
    try:
        # Discard stdout; inspect only the final 4 KiB of temporary stderr.
        # Never put raw traceback, source, missing module names or issue text
        # into the persistent report, provider feedback or model context.
        with tempfile.TemporaryFile() as errors:
            result = subprocess.run(
                args, stdout=subprocess.DEVNULL, stderr=errors, check=False,
                timeout=timeout)
            size = errors.seek(0, os.SEEK_END)
            errors.seek(max(0, size - 4096))
            category = _failure_category(
                result.returncode, errors.read(4096).decode("utf-8", "replace"))
        record(result.returncode, category)
        if use_native and result.returncode == 78:
            record(78, "runtime_provenance_unavailable")
            return None, False
        if result.returncode < 0 or result.returncode >= 128:
            return None, cleanup_failed()
        if result.returncode in (125, 126, 127):
            # A Docker/client failure cannot prove a code regression.
            return None, False
        return result.returncode, False
    except subprocess.TimeoutExpired:
        record(None, "probe_timeout")
        return None, cleanup_failed()
    except OSError:
        record(None, "docker_unavailable")
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
    if _approved_image() is None:
        return {"status": "skipped", "reason": "unapproved_runtime_image"}
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
    diagnostics = {}
    script, kind = _reproducer(issue, targets, root=root, evidence=diagnostics)
    if not script:
        return {"status": "skipped", "reason": "no_probe"}
    setup, profile = _bootstrap(targets)
    probe_cap = 12 if native_runtime.selected(targets) else 7
    fallback_cap = 8 if native_runtime.selected(targets) else 5
    diagnostics["baseline_bootstrap_profile"] = profile if kind in {"module_import", "source_doctest"} else "none"
    # Import setup is never prepended to public issue examples, which may
    # intentionally configure their own runtime. It applies only to our
    # developer-generated module-import probes (including import fallbacks).
    if kind in {"module_import", "source_doctest"}:
        script = setup + script
    def report(status, probe, reason):
        return {"status": status, "probe": probe, "reason": reason,
                **diagnostics}
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
            timeout=min(probe_cap, remaining / 2), diagnostics=diagnostics,
            phase="baseline")
        if unsafe_cleanup:
            return report("inconclusive", kind, "container_cleanup_unconfirmed")
        if before is None:
            return report("inconclusive", kind, "baseline_unavailable")
        if before != 0 and kind == "issue_python_example":
            # A failing issue example may intentionally demonstrate the bug.
            # First try an independent, frozen original-source behavior probe.
            alternate, alternate_kind = _reproducer("", targets, root=root,
                                                       evidence=diagnostics)
            remaining = timeout - (time.monotonic() - started)
            if alternate_kind == "source_doctest" and remaining >= 12:
                diagnostics["behavior_bootstrap_profile"] = profile
                code, cleanup_failure = _run_docker(
                    root, setup + alternate, overlay=None, targets=targets,
                    timeout=min(fallback_cap, remaining / 2), diagnostics=diagnostics,
                    phase="behavior_baseline")
                if cleanup_failure:
                    return report("inconclusive", kind, "container_cleanup_unconfirmed")
                if code == 0:
                    script, kind, before = setup + alternate, "source_doctest_fallback", 0
        if before != 0 and kind in {"issue_python_example", "source_doctest"}:
            # Public issue examples often *demonstrate* the existing bug,
            # so failing on original source is expected. The candidate
            # must not be judged by the example's failure alone. With
            # remaining budget, fall back to a weak import-only baseline
            # and report that distinct probe type transparently.
            fallback_script, fallback_kind = _import_probe(targets, root=root)
            fallback_script = setup + fallback_script
            remaining = timeout - (time.monotonic() - started)
            if fallback_kind == "module_import" and remaining >= 9:
                diagnostics["fallback_bootstrap_profile"] = profile
                fallback_before, cleanup_failure = _run_docker(
                    root, fallback_script, overlay=None, targets=targets,
                    timeout=min(fallback_cap, remaining / 2), diagnostics=diagnostics,
                    phase="fallback_baseline")
                if cleanup_failure:
                    return report("inconclusive", kind, "container_cleanup_unconfirmed")
                if fallback_before == 0:
                    script = fallback_script
                    kind = "module_import_fallback"
                    before = 0
                else:
                    return report("inconclusive", kind, "baseline_did_not_pass")
            else:
                return report("inconclusive", kind, "baseline_did_not_pass")
        if before != 0:
            # A failed original-code import is not evidence the proposed
            # candidate is broken. Do not upgrade to a false pass.
            return report("inconclusive", kind, "baseline_did_not_pass")
        remaining = timeout - (time.monotonic() - started)
        if remaining < 3:
            return report("skipped", kind, "deadline")
        after, unsafe_cleanup = _run_docker(
            root, script, overlay=staging, targets=targets,
            timeout=min(probe_cap, remaining), diagnostics=diagnostics,
            phase="candidate")
        if unsafe_cleanup or after is None:
            return report("inconclusive", kind, "candidate_or_cleanup_unavailable")
        if after != 0:
            return report("regression", kind, "baseline_passed_candidate_failed")
        return report("no_regression_observed", kind, "limited_probe_only")
