"""Read-only local Python symbol discovery. Does not execute user code."""
import ast
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Symbol:
    file: str
    name: str
    kind: str
    line: int

def index_python(root: Path, max_files: int = 300) -> list[Symbol]:
    root = root.resolve(strict=True)
    found = []
    count = 0
    for path in sorted(root.rglob("*.py")):
        if any(p in {".git",".venv","venv","__pycache__","node_modules"} for p in path.relative_to(root).parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        count += 1
        if count > max_files:
            raise ValueError("Too many Python files")
        if path.stat().st_size > 2_000_000:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (UnicodeError, SyntaxError):
            continue
        def visit(node, scope=()):
            for child in ast.iter_child_nodes(node):
                if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                    name = ".".join((*scope,child.name))
                    found.append(Symbol(path.relative_to(root).as_posix(),name,"class" if isinstance(child,ast.ClassDef) else "function",child.lineno))
                    visit(child,(*scope,child.name))
                else:
                    visit(child,scope)
        visit(tree)
    return found
