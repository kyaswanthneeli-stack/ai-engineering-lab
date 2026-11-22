"""Bounded, issue-aware source context for an untrusted Python repository.

Rank Python files by paths, symbols and issue terms without importing source.
An entry-budgeted directory walk avoids expanding an entire large repository
before limiting the index. All discovery is partial and read-only.
"""
from __future__ import annotations

import ast
from collections import Counter, deque
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox", ".mypy_cache", ".runs", ".pytest_cache", ".ruff_cache", "dist", "build"}
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")


def is_test_path(name: str) -> bool:
    """Recognize tests at any nesting depth, not only top-level tests/."""
    parts = PurePosixPath(name).parts
    filename = parts[-1] if parts else ""
    return (
        any(part in {"test", "tests"} for part in parts[:-1]) or
        filename.startswith("test_") or filename.endswith("_test.py") or
        filename in {"conftest.py", "runtests.py"}
    )


def is_test_infrastructure_issue(issue: str) -> bool:
    """Narrow opt-out for requests to repair testing machinery itself.

    A traceback mentioning a test file is not sufficient to make the issue
    test-focused: real regressions often reproduce through a test.
    """
    return bool(re.search(
        r"\b(?:test\s+(?:runner|discovery|collection|infrastructure|"
        r"configuration|fixtures?|harness)|(?:fix|repair|update|correct)"
        r"\s+(?:the\s+)?(?:broken\s+)?tests?\b|broken\s+tests?\b|"
        r"conftest\s+configuration)\b",
        issue[:12000], flags=re.IGNORECASE))


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



def _symlink_component(root: Path, name: str) -> bool:
    """Reject direct issue paths that traverse any symlinked component."""
    current = root
    for part in PurePosixPath(name).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


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
                not any(part in _SKIP for part in PurePosixPath(name).parts) and
                not _symlink_component(root, name) and target.is_file() and
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


def issue_identifiers(issue: str) -> tuple[str, ...]:
    """Bounded code-shaped tokens from the issue, not guessed solution hints."""
    tokens = re.findall(r"\b[A-Za-z_][A-Za-z_0-9]{2,79}\b", issue[:12000])
    counts = Counter(t for t in tokens if
                     ("_" in t and any(ch.isalpha() for ch in t)) or
                     (t.isupper() and len(t) >= 4) or
                     bool(re.search(r"[a-z][A-Z]", t)))
    return tuple(sorted(counts, key=lambda t: (-counts[t], -len(t), t))[:32])


def identifier_window(source: str, identifiers: tuple[str, ...], *, count: int = 80) -> int:
    """Choose a bounded line window around exact code-shaped token matches."""
    if not 1 <= count <= 120:
        raise ValueError("Invalid source window")
    if not identifiers:
        return 1
    wanted = set(identifiers)
    lines = source.splitlines()
    scores = []
    for line in lines:
        hits = set(re.findall(r"\b[A-Za-z_][A-Za-z_0-9]*\b", line)) & wanted
        scores.append(len(hits))
    best, start, running = 0, 0, 0
    for i, score in enumerate(scores):
        running += score
        if i >= count:
            running -= scores[i-count]
        if running > best:
            best, start = running, max(0, i-count+1)
    return start + 1


def ranked_source_context(repo: Path, issue: str, *, max_files: int = 8,
                          max_chars: int = 32000, scan_limit: int = 1800) -> list[ContextItem]:
    root = repo.resolve(strict=True)
    if (not root.is_dir() or not 1 <= max_files <= 20 or
            not 300 <= max_chars <= 100000 or not 1 <= scan_limit <= 20000):
        raise ValueError("Invalid context request")
    terms = _tokens(issue[:12000])
    test_infrastructure = is_test_infrastructure_issue(issue)
    candidates = []
    weighted = os.getenv("REPOPILOT_WEIGHT_RARE_TERMS", "").strip() == "1"
    frequencies = Counter()
    focused = os.getenv("REPOPILOT_IDENTIFIER_LOCALIZATION", "").strip() == "1"
    identifiers = set(issue_identifiers(issue)) if focused else set()
    exact_frequency = Counter()
    exact_hits = {}
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
        # A matching test assertion can repeat every issue term and outrank
        # the actual implementation. Prefer implementation files with a real
        # path/symbol overlap, but retain strongly related test files as
        # fallback and preserve explicit test-harness maintenance requests.
        implementation_match = (
            not test_infrastructure and not is_test_path(rel) and
            path_score + symbol_score > 0)
        priority = 0 if implementation_match else 1
        # Document frequencies are computed only over the bounded, safely
        # parsed source index. Generic words that occur throughout a project
        # should contribute less than distinctive issue/path/symbol terms.
        path_hits = terms & path_terms
        symbol_hits = terms & symbol_terms
        body_hits = terms & _tokens(source[:15000])
        if weighted:
            frequencies.update(path_hits | symbol_hits | body_hits)
        if identifiers:
            # Search the entire bounded source, including late methods and
            # configuration uses. Exact tokens avoid incidental substrings.
            hits = identifiers & set(re.findall(r"\b[A-Za-z_][A-Za-z_0-9]*\b", source))
            exact_hits[rel] = hits
            exact_frequency.update(hits)
        candidates.append((priority, score, rel, source, symbols,
                           path_hits, symbol_hits, body_hits))
    if weighted:
        count = len(candidates)
        def rarity(hit):
            return math.log1p(count / max(1, frequencies[hit]))
        def rerank(item):
            priority, _, rel, source, symbols, paths, names, body = item
            # Normalize the symbol contribution so very broad modules do not
            # win solely by exposing hundreds of unrelated declarations.
            name_score = sum(sorted((rarity(h) for h in names), reverse=True)[:8])
            path_score = sum(rarity(h) for h in paths)
            body_score = sum(sorted((rarity(h) for h in body), reverse=True)[:8])
            score = round(12 * path_score + 8 * name_score + 2 * body_score)
            return priority, score, rel, source, symbols, paths, names, body
        candidates = [rerank(item) for item in candidates]
    if identifiers:
        count = len(candidates)
        def exact_rerank(item):
            priority, score, rel, source, symbols, paths, names, body = item
            hits = exact_hits.get(rel, set())
            strength = sum(sorted((math.log1p(count / exact_frequency[h])
                                   for h in hits), reverse=True)[:8])
            if strength:
                score += round(36 * strength)
                if not test_infrastructure and not is_test_path(rel):
                    priority = 0
            return priority, score, rel, source, symbols, paths, names, body
        candidates = [exact_rerank(item) for item in candidates]
    candidates.sort(key=lambda x: (x[0], -x[1], x[2]))
    selected = []
    remaining = max_chars
    for _, score, rel, source, symbols, _, _, _ in candidates:
        if len(selected) >= max_files or remaining < 300:
            break
        max_per_file = min(9000, remaining)
        marker = "\n# [RepoPilot context truncated; do not assume missing lines]\n"
        if len(source) > max_per_file:
            # The warning counts against the prompt budget too.
            chunk = source[:max_per_file - len(marker)] + marker
        else:
            chunk = source
        remaining -= len(chunk)
        selected.append(ContextItem(rel, score, symbols[:80], chunk))
    return selected


def describe_context(items: list[ContextItem]) -> str:
    return "\n".join(
        f"FILE {item.path} [rank_score={item.score}; symbols={', '.join(item.symbols[:25])}]\n"
        + item.text + "\nEND FILE" for item in items
    )
