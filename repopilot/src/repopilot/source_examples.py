"""Select bounded original-source doctests as data; never import target code."""
from __future__ import annotations

import ast
import doctest
import hashlib
from pathlib import Path


def select_source_examples(root: Path, targets: list[str]) -> dict | None:
    """Choose one complete docstring with runnable, output-checking examples.

    Expected output comes from the pristine source, never from a proposed
    overlay. Skipped examples and import-only snippets are not behavioral
    evidence. Unsupported source/examples simply leave the probe unavailable.
    """
    for name in targets[:2]:
        path = root / name
        try:
            if (not path.is_file() or path.is_symlink()
                    or not path.resolve().is_relative_to(root.resolve())
                    or any((root / Path(*Path(name).parts[:n])).is_symlink()
                           for n in range(1, len(Path(name).parts) + 1))
                    or path.stat().st_size > 100_000):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            nodes = sorted((node for node in ast.walk(tree) if isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))),
                key=lambda node: getattr(node, "lineno", 0))
            for node in nodes:
                text = ast.get_docstring(node)
                if not text or len(text) > 6000:
                    continue
                examples = doctest.DocTestParser().get_examples(text)
                active = [e for e in examples if not e.options.get(doctest.SKIP, False)]
                if (not 1 <= len(examples) <= 8 or not active
                        or not any(e.want.strip() for e in active)
                        or sum(len(e.source) + len(e.want) for e in examples) > 2400):
                    continue
                return {"path": name, "definition": getattr(node, "name", "module"),
                        "example_count": len(active), "text": text,
                        "sha256": hashlib.sha256(text.encode()).hexdigest()}
        except (OSError, ValueError, SyntaxError, RecursionError):
            continue
    return None


def runner_script(selection: dict) -> str:
    """Run frozen examples against the imported original/candidate module.

    The caller must first import the selected module into `_module` and check
    its source origin. This code is executed only inside restricted Docker.
    """
    return (
        "import doctest\n"
        "_test = doctest.DocTestParser().get_doctest(" + repr(selection["text"]) +
        ", dict(_module.__dict__), 'original_source_examples', '<source_examples>', 0)\n"
        "_runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)\n"
        "_result = _runner.run(_test, out=lambda text: None)\n"
        "assert _result.attempted > 0, 'no_source_examples_executed'\n"
        "assert _result.failed == 0, 'original_source_examples_failed'\n"
    )
