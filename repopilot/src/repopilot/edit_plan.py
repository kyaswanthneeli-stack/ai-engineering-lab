"""Turn tightly scoped model search/replace edits into validated git diffs.

No arbitrary file creation, deletion, shell commands or fuzzy matching.
The model must provide existing source text that matches exactly once.
All transformations happen in memory, without changing the repository.
"""
from __future__ import annotations

import difflib
from pathlib import Path, PurePosixPath
from .patches import validate_patch


class EditPlanError(ValueError):
    pass


def canonical_patch(repo: Path, edits: list[dict], *, allowed_files: set[str]) -> str:
    root = repo.resolve(strict=True)
    if not isinstance(edits, list) or not 1 <= len(edits) <= 12:
        raise EditPlanError("Require between 1 and 12 exact source replacements")
    originals: dict[str, str] = {}
    changed: dict[str, str] = {}
    for item in edits:
        if not isinstance(item, dict) or set(item) != {"path", "old", "new"}:
            raise EditPlanError("Each edit requires only path, old and new")
        name, old, new = item["path"], item["old"], item["new"]
        if not isinstance(name, str) or name not in allowed_files:
            raise EditPlanError("Edit path was not supplied to the model")
        p = PurePosixPath(name)
        if (p.is_absolute() or ".." in p.parts or "\\" in name or
                not name.endswith(".py") or ".git" in p.parts):
            raise EditPlanError("Unsafe Python edit path")
        if (not isinstance(old, str) or not isinstance(new, str) or
                not 1 <= len(old) <= 6000 or not 1 <= len(new) <= 6000 or old == new):
            raise EditPlanError("Replacements must be distinct, nonempty, and bounded")
        path = root.joinpath(*p.parts)
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise EditPlanError("Edit target is not an existing regular file")
        if path.stat().st_size > 100_000:
            raise EditPlanError("Edit target exceeds size limit")
        if name not in originals:
            source = path.read_text(encoding="utf-8")
            if not source.endswith("\n"):
                raise EditPlanError("Only newline-terminated Python files supported")
            originals[name] = source
            changed[name] = source
        source = changed[name]
        if source.count(old) != 1:
            raise EditPlanError("Exact old text must occur once in the current source")
        changed[name] = source.replace(old, new, 1)
    if len(changed) > 8:
        raise EditPlanError("Maximum 8 modified source files")

    parts = []
    for name in sorted(changed):
        if originals[name] == changed[name]:
            continue
        diff = "".join(difflib.unified_diff(
            originals[name].splitlines(keepends=True),
            changed[name].splitlines(keepends=True),
            fromfile="a/" + name, tofile="b/" + name, n=3))
        parts.append(f"diff --git a/{name} b/{name}\n" + diff)
    patch = "".join(parts)
    if not patch:
        raise EditPlanError("No source modifications")
    validate_patch(patch)
    return patch
