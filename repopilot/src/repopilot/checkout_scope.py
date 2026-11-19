"""Choose a safe module subdirectory inside an already pinned checkout."""
from __future__ import annotations
from pathlib import Path, PurePosixPath

def resolve_repo_subdir(repo:Path,subdir:str)->Path:
    root=repo.resolve(strict=True)
    if not subdir or subdir==".":
        return root
    p=PurePosixPath(subdir)
    if (p.is_absolute() or ".." in p.parts or "\\" in subdir
            or not all(part not in {"", ".", ".git"} for part in p.parts)):
        raise ValueError("Unsafe checkout subdirectory")
    target=root.joinpath(*p.parts)
    if target.is_symlink() or not target.is_dir():
        raise ValueError("Checkout subdirectory must be an existing directory")
    resolved=target.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError("Checkout subdirectory escaped repository")
    return resolved
