"""Static, conservative quote-only proposal check; never execute target Python.

This is a repair-quality heuristic, not an equivalence proof. It preserves
comments, token positions and all non-literal tokens, and normalizes only
ordinary string/bytes literals with identical values. Source-reflection bugs
can legitimately depend on quotes; operators can disable the agent gate.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tokenize

from .patches import apply_patch
from .pr import patch_targets

_SAFE_PATH = re.compile(r"[A-Za-z0-9_./-]{1,240}\Z")


def _literal_normalized_tokens(source: str) -> list:
    # Parsing validates indentation/syntax, without importing or evaluating it.
    ast.parse(source, type_comments=True)
    tokens = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        value = token.string
        if token.type == tokenize.STRING:
            try:
                literal = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                pass  # f-strings and unsupported syntax remain exact tokens.
            else:
                if isinstance(literal, (str, bytes)):
                    value = (type(literal).__name__, literal)
        tokens.append((token.type, value, token.start, token.end))
    return tokens


def review_quote_only_patch(repo: Path, patch: str) -> dict:
    """Compare at most eight bounded files in a private data-only overlay.

    Unavailable/unsupported analysis never becomes a passing test or a no-op
    verdict. Original pinned files remain unchanged for every patch schema.
    """
    try:
        root = repo.resolve(strict=True)
        targets = patch_targets(patch)
        if not 1 <= len(targets) <= 8:
            raise ValueError("Target limit")
        with tempfile.TemporaryDirectory(prefix="repopilot-quality-") as tmp:
            staging = Path(tmp)
            originals = {}
            for name in targets:
                path = root / name
                if (not _SAFE_PATH.fullmatch(name)
                        or ".." in Path(name).parts
                        or not path.is_file()
                        or not path.resolve().is_relative_to(root)
                        or any((root / Path(*Path(name).parts[:n])).is_symlink()
                               for n in range(1, len(Path(name).parts) + 1))
                        or path.stat().st_size > 100_000):
                    raise ValueError("Unsafe or large target")
                originals[name] = path.read_text(encoding="utf-8")
                destination = staging / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)
            apply_patch(staging, patch)
            # Check every modified file before returning a quote-only or
            # changed verdict. A syntactically valid baseline must never
            # become uncompilable. Compilation creates a code object only;
            # no source is executed. Unsupported historical baseline syntax
            # remains explicitly unavailable rather than a false regression.
            changed = False
            unavailable = False
            for name in targets:
                candidate = staging / name
                if candidate.stat().st_size > 100_000:
                    unavailable = True
                    continue
                updated = candidate.read_text(encoding="utf-8")
                try:
                    compile(originals[name], name, "exec", dont_inherit=True)
                except SyntaxError:
                    unavailable = True
                    continue
                try:
                    compile(updated, name, "exec", dont_inherit=True)
                except SyntaxError:
                    return {"status": "invalid_python",
                            "reason": "candidate_introduced_compile_error"}
                try:
                    before = _literal_normalized_tokens(originals[name])
                    after = _literal_normalized_tokens(updated)
                except (ValueError, SyntaxError, tokenize.TokenError, RecursionError):
                    unavailable = True
                    continue
                changed |= before != after
            if unavailable:
                return {"status": "unavailable", "reason": "static_analysis_unavailable"}
            if changed:
                return {"status": "changed_or_unknown",
                        "reason": "tokens_or_positions_differ"}
        return {"status": "quote_only",
                "reason": "equal_literal_values_and_other_tokens"}
    except (OSError, ValueError, SyntaxError, tokenize.TokenError,
            RecursionError, subprocess.TimeoutExpired):
        return {"status": "unavailable", "reason": "static_analysis_unavailable"}
