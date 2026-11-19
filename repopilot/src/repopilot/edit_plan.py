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


def canonical_line_patch(repo: Path, edits: list[dict], *,
                         allowed_files: set[str],
                         inspected_windows: dict[str, list[tuple[int, int]]]) -> str:
    """Build a patch from line ranges actually exposed by bounded read tools.

    Line coordinates are anchored to the ORIGINAL file and never authorized by
    untrusted issue text or model claims. No fuzzy matching, file creation,
    executable model commands, or write access. Each changed line must have
    appeared in a single safe inspected source window.
    """
    if not isinstance(edits, list) or not 1 <= len(edits) <= 12:
        raise EditPlanError("Require 1–12 inspected source line replacements")
    root = repo.resolve(strict=True)
    source_by_path: dict[str, list[str]] = {}
    replacements: dict[str, list[tuple[int, int, list[str]]]] = {}
    for item in edits:
        if not isinstance(item, dict) or set(item) != {"path", "start_line", "end_line", "new"}:
            raise EditPlanError("Each line edit requires only path, start_line, end_line, new")
        name, start, end, new = (
            item["path"], item["start_line"], item["end_line"], item["new"])
        if not isinstance(name, str) or name not in allowed_files:
            raise EditPlanError("Line edit path was not inspected")
        posix = PurePosixPath(name)
        if (posix.is_absolute() or ".." in posix.parts or
                "\\" in name or ".git" in posix.parts or
                not name.endswith(".py")):
            raise EditPlanError("Unsafe Python line edit path")
        if (type(start) is not int or type(end) is not int or
                not 1 <= start <= end <= 100_000 or end - start >= 12):
            raise EditPlanError("Line edit range exceeds 12 original lines")
        if not any(type(lo) is int and type(hi) is int and
                   lo <= start <= end <= hi
                   for lo, hi in inspected_windows.get(name, [])):
            raise EditPlanError("Line edit range outside inspected window")
        if not isinstance(new, str) or not new or len(new) > 3000 or "\x00" in new:
            raise EditPlanError("Invalid bounded replacement line text")
        if new.count("\n") > 20:
            raise EditPlanError("Too many replacement lines")
        path = root.joinpath(*posix.parts)
        if (path.is_symlink() or not path.is_file() or
                not path.resolve().is_relative_to(root) or
                path.stat().st_size > 100_000):
            raise EditPlanError("Line edit target is not an allowed regular source")
        if name not in source_by_path:
            source = path.read_text(encoding="utf-8")
            if not source.endswith("\n"):
                raise EditPlanError("Only newline-terminated Python files supported")
            source_by_path[name] = source.splitlines(keepends=True)
        lines = source_by_path[name]
        if end > len(lines) or any(len(line.rstrip("\r\n")) > 320
                                   for line in lines[start-1:end]):
            raise EditPlanError("Line edit targets unseen or truncated source")
        current = "".join(lines[start-1:end])
        replacement = new if new.endswith("\n") else new + "\n"
        if current == replacement:
            raise EditPlanError("Line edit makes no source modification")
        replacements.setdefault(name, []).append(
            (start-1, end, replacement.splitlines(keepends=True)))
    if len(replacements) > 8:
        raise EditPlanError("Maximum 8 modified source files")
    parts = []
    for name in sorted(replacements):
        orig = source_by_path[name]
        edits_for_file = sorted(replacements[name])
        for previous, current in zip(edits_for_file, edits_for_file[1:]):
            if current[0] < previous[1]:
                raise EditPlanError("Overlapping inspected line ranges")
        changed = orig[:]
        for start, end, new_lines in reversed(edits_for_file):
            changed[start:end] = new_lines
        if orig == changed:
            raise EditPlanError("No source modifications")
        diff = "".join(difflib.unified_diff(
            orig, changed, fromfile="a/" + name, tofile="b/" + name, n=3))
        parts.append(f"diff --git a/{name} b/{name}\n" + diff)
    patch = "".join(parts)
    validate_patch(patch)
    return patch
