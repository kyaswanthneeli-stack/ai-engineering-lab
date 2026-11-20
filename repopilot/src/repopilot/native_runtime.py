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


def source_guard(*, report: bool = False) -> str:
    """Compare tracked blob identities, permitting only executable-bit changes.

    Docker preparation can commit chmod changes. core.fileMode alone cannot
    ignore modes already stored in commits, so compare blob IDs and file kinds
    directly. Still reject source additions/deletions, changed bytes, symlink
    conversions and dirty tracked source in the image's working tree.
    """
    code = (
        "import subprocess as _sp, json as _json\n"
        "def _git(*args):\n"
        "    return _sp.run(['git','-c','safe.directory=/testbed','-c','core.fileMode=false','-C','/testbed',*args], "
        "stdout=_sp.PIPE, stderr=_sp.DEVNULL, timeout=3, check=True).stdout\n"
        "def _tree(ref):\n"
        "    result = {}\n"
        "    for entry in _git('ls-tree','-r','-z',ref,'--','lib/matplotlib','src','extern').split(b'\\0'):\n"
        "        if not entry: continue\n"
        "        meta, name = entry.split(b'\\t',1)\n"
        "        mode, kind, blob = meta.split()\n"
        "        result[name] = (int(mode,8) & 0o170000, kind, blob)\n"
        "    return result\n"
        "try:\n"
        "    _head = _git('rev-parse','HEAD').decode().strip()\n"
        "    _base_tree = _tree(" + repr(MATPLOTLIB_BASE) + ")\n"
        "    _head_tree = _tree('HEAD')\n"
        "    _source_match = bool(_base_tree) and _base_tree == _head_tree\n"
        "    _git('diff','--quiet','HEAD','--','lib/matplotlib','src','extern')\n"
    )
    if report:
        code += ("    print(_json.dumps({'expected_base':" + repr(MATPLOTLIB_BASE) +
                 ",'image_head':_head,'source_blob_identities_match':_source_match,"
                 "'checked_source_files':len(_base_tree)}),flush=True)\n")
    return code + (
        "    if not _source_match: raise SystemExit(78)\n"
        "except (OSError, ValueError, _sp.SubprocessError): raise SystemExit(78)\n"
    )


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
    return source_guard() + (
        "import hashlib as _hash, importlib.util as _iu, sys as _sys\n"
        "from pathlib import Path as _Path\n"
        "try:\n"
        "    for _name, _digest in " + repr(expected) + ".items():\n"
        "        if _hash.sha256((_Path('/testbed')/_name).read_bytes()).hexdigest() != _digest: raise SystemExit(78)\n"
        "except OSError: raise SystemExit(78)\n"
        "_spec = _iu.spec_from_file_location('matplotlib','/workspace/lib/matplotlib/__init__.py',"
        "submodule_search_locations=['/workspace/lib/matplotlib','/testbed/lib/matplotlib'])\n"
        "_mpl = _iu.module_from_spec(_spec)\n"
        "_sys.modules['matplotlib'] = _mpl\n"
        "_spec.loader.exec_module(_mpl)\n"
        "assert _Path(_mpl.__file__).resolve() == _Path('/workspace/lib/matplotlib/__init__.py')\n"
    )
