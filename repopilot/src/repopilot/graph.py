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

def dependent_modules(graph:dict, changed_modules:list[str], *, max_depth:int=5)->dict:
    """Conservative reverse-import impact, never claiming runtime call coverage.

    Return shortest static dependency distances from changed modules.
    Paths are module names emitted by import_graph(), not arbitrary file paths.
    """
    if not isinstance(max_depth,int) or not 1 <= max_depth <= 20:
        raise ValueError("max_depth must be in 1..20")
    known=set(graph["modules"])
    if not isinstance(changed_modules,list) or not changed_modules or any(
            not isinstance(name,str) or name not in known for name in changed_modules):
        raise ValueError("All changed modules must exist in the static graph")
    reverse={m:set() for m in known}
    for edge in graph["imports"]:
        src,dst=edge["from"],edge["to"]
        if src in known and dst in known:
            reverse[dst].add(src)
    levels={name:0 for name in changed_modules}
    frontier=set(changed_modules)
    for distance in range(1,max_depth+1):
        next_frontier=set()
        for module in frontier:
            for dependent in reverse[module]:
                if dependent not in levels:
                    levels[dependent]=distance
                    next_frontier.add(dependent)
        frontier=next_frontier
        if not frontier:
            break
    return {"changed":sorted(set(changed_modules)),
            "dependents":[{"module":name,"distance":levels[name]}
                          for name in sorted(levels,key=lambda n:(levels[n],n))
                          if levels[name]>0],
            "max_depth":max_depth,
            "scope":"Static reverse-import candidates only; no execution or runtime call graph."}
