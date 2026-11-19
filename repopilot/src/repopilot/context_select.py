"""Bounded, issue-aware source context for an untrusted repository.

Rank Python files using symbols, paths and issue terms. Parse but never import
target modules. Read only files within the resolved workspace and reject links.
The score is heuristic and deliberately does not claim semantic understanding.
"""
from __future__ import annotations
import ast
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_SKIP={".git",".venv","venv","node_modules","__pycache__",".tox",".mypy_cache"}
_WORD=re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")

@dataclass(frozen=True)
class ContextItem:
    path:str
    score:int
    symbols:tuple[str,...]
    text:str

def _tokens(s:str)->set[str]:
    return {w.lower() for w in _WORD.findall(s)}

def _safe_python_paths(root:Path,max_files:int):
    count=0
    for path in sorted(root.rglob("*.py")):
        rel=path.relative_to(root)
        if any(part in _SKIP for part in rel.parts):
            continue
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            continue
        count+=1
        if count>max_files:
            break  # Partial index, not a complete search
        if path.stat().st_size>100_000:
            continue
        yield path,rel.as_posix()

def ranked_source_context(repo:Path,issue:str,*,max_files:int=8,max_chars:int=32000,scan_limit:int=1800)->list[ContextItem]:
    root=repo.resolve(strict=True)
    if not root.is_dir() or not 1<=max_files<=20 or not 300<=max_chars<=100000:
        raise ValueError("Invalid context request")
    terms=_tokens(issue[:12000])
    candidates=[]
    # Issue-referenced files get priority in large repositories.
    mentions=set(re.findall(r"[A-Za-z0-9_./-]+\.py", issue[:12000]))
    explicit=[]
    for name in sorted(mentions):
        target=root/name
        if (not name.startswith("/") and ".." not in Path(name).parts and
                target.is_file() and not target.is_symlink() and
                target.resolve().is_relative_to(root) and target.stat().st_size<=100000):
            explicit.append((target,name))
    # A traceback often gives only a basename (e.g. config.py) while the
    # repository stores it under a package. Search only that exact basename,
    # with a finite candidate cap, independently of the regular scan limit.
    # Never allow issue text to escape the workspace or read symlink targets.
    nested=[]
    for name in sorted(mentions):
        base=PurePosixPath(name).name
        if not base or base!=name or not base.endswith(".py"):
            continue
        for target in root.rglob(base):
            rel=target.relative_to(root)
            if any(part in _SKIP for part in rel.parts):
                continue
            if (target.is_symlink() or not target.is_file() or
                    not target.resolve().is_relative_to(root) or
                    target.stat().st_size>100000):
                continue
            nested.append((target,rel.as_posix()))
            if len(nested)>=24:
                break
        if len(nested)>=24:
            break
    visited=set()
    for path,rel in [*explicit,*nested,*_safe_python_paths(root,scan_limit)]:
        if rel in visited:
            continue
        visited.add(rel)
        try:
            source=path.read_text(encoding="utf-8")
            tree=ast.parse(source)
        except (SyntaxError,UnicodeError,ValueError):
            continue
        symbols=tuple(node.name for node in ast.walk(tree)
            if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)))
        path_terms=_tokens(rel.replace("/"," "))
        symbol_terms=set()
        for symbol in symbols:
            symbol_terms |= _tokens(symbol.replace("_"," "))
            symbol_terms.add(symbol.lower())
        path_score=12*len(terms & path_terms)
        symbol_score=8*len(terms & symbol_terms)
        # Body matches are weaker than path and symbol evidence.
        body_score=min(8,len(terms & _tokens(source[:15000])))
        score=path_score+symbol_score+body_score
        candidates.append((score,rel,source,symbols))
    candidates.sort(key=lambda x:(-x[0],x[1]))
    selected=[]
    remaining=max_chars
    for score,rel,source,symbols in candidates:
        if len(selected)>=max_files or remaining<300:
            break
        # Prefer a smaller chunk to exhausting all context with one huge file.
        max_per_file=min(9000,remaining)
        chunk=source[:max_per_file]
        if len(source)>len(chunk):
            chunk+="\n# [RepoPilot context truncated; do not assume missing lines]\n"
        remaining-=len(chunk)
        selected.append(ContextItem(rel,score,symbols[:80],chunk))
    return selected


_TRACEBACK_LINE = re.compile(
    r"(?P<path>[A-Za-z0-9_./-]+\.py)[\"']?\s*(?::|,\s*line\s+)(?P<line>\d+)",
    re.IGNORECASE,
)


def issue_window_start(repo: Path, relative_path: str, issue: str, *,
                       count: int = 120) -> int:
    """Choose a bounded read window inside an already selected Python file.

    A traceback line takes precedence; otherwise use AST function/class
    symbols mentioned in the issue. The fallback is line one. No target
    code is executed and this never expands the editable-file allowlist.
    """
    root = repo.resolve(strict=True)
    path = PurePosixPath(relative_path) if isinstance(relative_path, str) else None
    if (not root.is_dir() or path is None or path.is_absolute() or
            ".." in path.parts or "\\" in relative_path or
            not relative_path.endswith(".py") or
            not isinstance(count, int) or not 1 <= count <= 120):
        raise ValueError("Unsafe issue window")
    target = root.joinpath(*path.parts)
    if (target.is_symlink() or not target.is_file() or
            not target.resolve().is_relative_to(root) or
            target.stat().st_size > 120_000):
        raise ValueError("Issue window target is not a safe Python file")
    source = target.read_text(encoding="utf-8")
    lines = source.splitlines()
    if len(lines) <= count:
        return 1
    max_start = len(lines) - count + 1

    # A traceback's original file and line is more useful than a top-of-file
    # excerpt, but a line in some other file cannot redirect inspection.
    basename = path.name
    for match in _TRACEBACK_LINE.finditer(issue[:12000]):
        mentioned = match.group("path")
        if (mentioned == relative_path or
                mentioned.endswith("/" + relative_path) or
                mentioned == basename):
            line_no = int(match.group("line"))
            if 1 <= line_no <= len(lines):
                return min(max(1, line_no - 12), max_start)

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 1
    raw_issue = issue[:12000].lower()
    terms = _tokens(raw_issue.replace("_", " "))
    names = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    best_score, best_line = 0, 1
    for node in ast.walk(tree):
        if not isinstance(node, names):
            continue
        symbol = node.name.lower()
        overlap = terms & _tokens(symbol.replace("_", " "))
        score = (150 if len(symbol) >= 5 and symbol in raw_issue else 0)
        score += 12 * len(overlap)
        if score > best_score:
            best_score, best_line = score, node.lineno
    return min(max(1, best_line - 12), max_start) if best_score else 1


def describe_context(items:list[ContextItem])->str:
    return "\n".join(
        f"FILE {item.path} [rank_score={item.score}; symbols={', '.join(item.symbols[:25])}]\n"
        +item.text+"\nEND FILE" for item in items
    )
