"""Conservative static module-import graph for Python repositories.

Never imports or executes target code. Edges are static candidates only:
dynamic imports, plugin loading and runtime dispatch are not represented.
"""
from __future__ import annotations
import ast
from pathlib import Path
from .context_select import _safe_python_paths

def module_name(path:str)->str:
    if path.endswith("/__init__.py"):
        return path[:-len("/__init__.py")].replace("/",".")
    if path=="__init__.py":
        return ""
    return path[:-3].replace("/",".")

def import_graph(root:Path,max_files:int=300)->dict:
    root=root.resolve(strict=True)
    records=[]
    for path,relative in _safe_python_paths(root,max_files):
        try:
            tree=ast.parse(path.read_text(encoding="utf-8"))
        except (UnicodeError,SyntaxError):
            continue
        records.append((relative,module_name(relative),tree))
    known={module for _,module,_ in records if module}
    edges=set()
    for relative,source,tree in records:
        for node in ast.walk(tree):
            targets=[]
            if isinstance(node,ast.Import):
                targets=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom):
                package=source.split(".")[:-1]
                # Relative from x import y: resolve package anchor only; conservative.
                if node.level:
                    parts=package[:max(0,len(package)-(node.level-1))]
                    base=".".join(parts+([node.module] if node.module else []))
                else:
                    base=node.module or ""
                targets=[base]
                targets.extend(f"{base}.{a.name}" for a in node.names if base)
            for target in targets:
                parts=target.split(".")
                # Resolve to the longest known local module, not third-party libraries.
                matches=[".".join(parts[:n]) for n in range(len(parts),0,-1)
                         if ".".join(parts[:n]) in known]
                if matches and matches[0]!=source:
                    edges.add((source,matches[0]))
    return {
        "modules":sorted(known),
        "imports":[{"from":src,"to":dst} for src,dst in sorted(edges)],
        "scope":"Static imports only; no runtime call graph or execution."
    }
