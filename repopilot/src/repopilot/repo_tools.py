"""Read-only, bounded source inspection tools for model-driven investigation."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import re
from .context_select import _safe_python_paths


class InspectionError(ValueError):
    pass


def _safe_file(root: Path, name: str) -> Path:
    if not isinstance(name, str) or len(name)>240:
        raise InspectionError("Invalid source path")
    pure=PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or "\\" in name or not name.endswith(".py"):
        raise InspectionError("Path outside allowed Python source")
    path=root.joinpath(*pure.parts)
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise InspectionError("Source is not an allowed regular file")
    if path.stat().st_size>120_000:
        raise InspectionError("Source is larger than allowed inspection limit")
    return path


def list_python_files(repo: Path, *, prefix: str="", limit:int=60) -> dict:
    root=repo.resolve(strict=True)
    if not isinstance(prefix,str) or len(prefix)>120 or ".." in PurePosixPath(prefix).parts or prefix.startswith("/") or "\\" in prefix:
        raise InspectionError("Unsafe prefix")
    if not 1<=limit<=100:
        raise InspectionError("Limit must be bounded")
    items=[]
    for _,name in _safe_python_paths(root,2000):
        if name.startswith(prefix):
            items.append(name)
            if len(items)>=limit:
                break
    return {"files":items,"truncated":len(items)==limit}


def search_python(repo: Path, query: str, *, limit:int=15) -> dict:
    root=repo.resolve(strict=True)
    if not isinstance(query,str) or not 2<=len(query)<=100 or not 1<=limit<=30:
        raise InspectionError("Invalid bounded literal query")
    found=[]
    needle=query.casefold()
    for path,name in _safe_python_paths(root,2000):
        for line_no,line in enumerate(path.read_text(encoding="utf-8",errors="replace").splitlines(),1):
            if needle in line.casefold():
                found.append({"path":name,"line":line_no,"excerpt":line[:220]})
                if len(found)>=limit:
                    return {"matches":found,"truncated":True}
    return {"matches":found,"truncated":False}


def read_python(repo: Path, name: str, *, start:int=1, count:int=80) -> dict:
    root=repo.resolve(strict=True)
    if not 1<=start<=100_000 or not 1<=count<=120:
        raise InspectionError("Unsafe source line range")
    file=_safe_file(root,name)
    lines=file.read_text(encoding="utf-8").splitlines()
    excerpt=[{"line":i+1,"text":lines[i][:320]} for i in range(start-1,min(len(lines),start+count-1))]
    return {"path":name,"total_lines":len(lines),"lines":excerpt}
