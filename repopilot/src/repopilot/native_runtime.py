"""Explicit digest-pinned Matplotlib native support for one verified checkout.

Python source always comes from the read-only pinned /workspace checkout.
Only native/built assets may fall back to the official instance image. No target
build/install scripts run on the host, and no model-supplied image is accepted.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

MATPLOTLIB_BASE = "c33557d120eefe3148ebfcf2e758ff2357966000"
MATPLOTLIB_IMAGE = (
    "swebench/sweb.eval.x86_64.matplotlib_1776_matplotlib-22835@"
    "sha256:ffe240330bab2ef382e4aba3e09fd624dccef459312defe3c815a58c4a0edd47"
)
NATIVE_PYTHON = "/opt/miniconda3/envs/testbed/bin/python"


def selected(targets: list[str]) -> bool:
    return (os.getenv("REPOPILOT_CANDIDATE_MATPLOTLIB_NATIVE", "0").strip() == "1"
            and bool(targets) and all(path.startswith("lib/matplotlib/") for path in targets))


def prefix(repo: Path, targets: list[str]) -> str:
    """Validate native-image source alignment before loading workspace Python.

    The official image can have a setup commit after the dataset base. Require
    zero tracked differences in package/native source against the exact base,
    plus exact original target-file hashes. A mismatch exits 78 and is never
    treated as candidate success or a code regression.
    """
    expected = {}
    for name in targets:
        path = repo / name
        if (not name.startswith("lib/matplotlib/") or ".." in Path(name).parts
                or path.is_symlink() or not path.resolve().is_relative_to(repo.resolve())
                or any((repo / Path(*Path(name).parts[:n])).is_symlink()
                       for n in range(1, len(Path(name).parts) + 1))
                or not path.is_file() or path.stat().st_size > 100_000):
            raise ValueError("Unsafe native runtime target")
        expected[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return (
        "import subprocess as _sp, hashlib as _hash, importlib.util as _iu, sys as _sys\n"
        "from pathlib import Path as _Path\n"
        "try:\n"
        "    _diff = _sp.run(['git','-c','safe.directory=/testbed','-c','core.fileMode=false','-C','/testbed',"
        "'diff','--quiet'," + repr(MATPLOTLIB_BASE) +
        ",'--','lib/matplotlib','src','extern'], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL, timeout=3)\n"
        "    if _diff.returncode != 0: raise SystemExit(78)\n"
        "    for _name, _digest in " + repr(expected) + ".items():\n"
        "        if _hash.sha256((_Path('/testbed')/_name).read_bytes()).hexdigest() != _digest: raise SystemExit(78)\n"
        "except (OSError, _sp.TimeoutExpired): raise SystemExit(78)\n"
        "_spec = _iu.spec_from_file_location('matplotlib','/workspace/lib/matplotlib/__init__.py',"
        "submodule_search_locations=['/workspace/lib/matplotlib','/testbed/lib/matplotlib'])\n"
        "_mpl = _iu.module_from_spec(_spec)\n"
        "_sys.modules['matplotlib'] = _mpl\n"
        "_spec.loader.exec_module(_mpl)\n"
        "assert _Path(_mpl.__file__).resolve() == _Path('/workspace/lib/matplotlib/__init__.py')\n"
    )
