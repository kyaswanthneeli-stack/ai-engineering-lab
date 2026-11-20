"""Bounded, issue-aware source context for an untrusted Python repository.

Rank Python files by paths, symbols and issue terms without importing source.
An entry-budgeted directory walk avoids expanding an entire large repository
before limiting the index. All discovery is partial and read-only.
"""
from __future__ import annotations

import ast
from collections import deque
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox", ".mypy_cache"}
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")


@dataclass(frozen=True)
class ContextItem:
    path: str
    score: int
    symbols: tuple[str, ...]
    text: str


def _tokens(s: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(s)}


def _bounded_python_walk(root: Path, *, entry_limit: int):
    """Yield safe Python paths, stopping after a finite directory-entry budget.

    We do not use rglob(), which expands an entire repository before a Python
    loop can enforce scan_limit. Breadth-first enumeration also reduces bias
    toward the first enormous package. A partial result is explicitly allowed.
    """
    queue = deque([root])
    seen = 0
    while queue and seen < entry_limit:
        directory = queue.popleft()
        entries = []
        try:
            with os.scandir(directory) as stream:
                for entry in stream:
                    if seen >= entry_limit:
                        break
                    seen += 1
                    if entry.name not in _SKIP:
                        entries.append(entry)
        except OSError:
            continue
        for entry in sorted(entries, key=lambda item: item.name):
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    queue.append(Path(entry.path))
                    continue
                if not entry.name.endswith(".py") or not entry.is_file(follow_symlinks=False):
                    continue
                if entry.stat(follow_symlinks=False).st_size > 100_000:
                    continue
                path = Path(entry.path)
                if not path.resolve().is_relative_to(root):
                    continue
                yield path, path.relative_to(root).as_posix()
            except (OSError, RuntimeError, ValueError):
                continue


def _safe_python_paths(root: Path, max_files: int):
    """Shared finite source iterator for agent tools and import-graph analysis.

    Preserve the existing helper contract so model-directed list/search and
    static import analysis benefit from the same guarded, bounded traversal.
    """
    if not 1 <= max_files <= 20000:
        raise ValueError("Python source scan limit outside safe bounds")
    root = root.resolve(strict=True)
    count = 0
    for path, relative in _bounded_python_walk(
            root, entry_limit=max(500, max_files * 8)):
        yield path, relative
        count += 1
        if count >= max_files:
            break


def _candidate_paths(root: Path, issue: str, scan_limit: int):
    """Prioritize explicit issue paths and nested basename matches.

    The regular source index is capped by scan_limit. Basename matching gets
    a separate bounded enumeration budget, so a traceback naming 'module.py'
    can still find 'pkg/module.py' beyond the normal scan limit.
    """
    mentions = set(re.findall(r"[A-Za-z0-9_./-]+\.py", issue[:12000]))
    explicit = []
    basenames = set()
    for name in sorted(mentions):
        if (PurePosixPath(name).name == name and
                name.endswith(".py")):
            basenames.add(name)
        target = root / name
        if (not name.startswith("/") and ".." not in PurePosixPath(name).parts and
                not target.is_symlink() and target.is_file() and
                target.resolve().is_relative_to(root) and
                target.stat().st_size <= 100_000):
            explicit.append((target, name))

    normal = []
    nested = []
    # Hard upper bound on all directory entries examined, not merely on
    # files yielded. When basenames are named, search a larger but still
    # finite window before falling back to the normal capped source index.
    entry_limit = max(500, scan_limit * (8 if basenames else 4))
    for path, rel in _bounded_python_walk(root, entry_limit=entry_limit):
        if len(normal) < scan_limit:
            normal.append((path, rel))
        if basenames and path.name in basenames and len(nested) < 24:
            nested.append((path, rel))
        if len(normal) >= scan_limit and (not basenames or len(nested) >= 24):
            break

    visited = set()
    for path, rel in [*explicit, *nested, *normal]:
        if rel not in visited:
            visited.add(rel)
            yield path, rel


def ranked_source_context(repo: Path, issue: str, *, max_files: int = 8,
                          max_chars: int = 32000, scan_limit: int = 1800) -> list[ContextItem]:
    root = repo.resolve(strict=True)
    if (not root.is_dir() or not 1 <= max_files <= 20 or
            not 300 <= max_chars <= 100000 or not 1 <= scan_limit <= 20000):
        raise ValueError("Invalid context request")
    terms = _tokens(issue[:12000])
    candidates = []
    for path, rel in _candidate_paths(root, issue, scan_limit):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError, UnicodeError, ValueError):
            continue
        symbols = tuple(node.name for node in ast.walk(tree)
                        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)))
        path_terms = _tokens(rel.replace("/", " "))
        symbol_terms = set()
        for symbol in symbols:
            symbol_terms |= _tokens(symbol.replace("_", " "))
            symbol_terms.add(symbol.lower())
        path_score = 12 * len(terms & path_terms)
        symbol_score = 8 * len(terms & symbol_terms)
        body_score = min(8, len(terms & _tokens(source[:15000])))
        score = path_score + symbol_score + body_score
        candidates.append((score, rel, source, symbols))
    candidates.sort(key=lambda x: (-x[0], x[1]))
    selected = []
    remaining = max_chars
    for score, rel, source, symbols in candidates:
        if len(selected) >= max_files or remaining < 300:
            break
        max_per_file = min(9000, remaining)
        chunk = source[:max_per_file]
        if len(source) > len(chunk):
            chunk += "\n# [RepoPilot context truncated; do not assume missing lines]\n"
        remaining -= len(chunk)
        selected.append(ContextItem(rel, score, symbols[:80], chunk))
    return selected


def describe_context(items: list[ContextItem]) -> str:
    return "\n".join(
        f"FILE {item.path} [rank_score={item.score}; symbols={', '.join(item.symbols[:25])}]\n"
        + item.text + "\nEND FILE" for item in items
    )
