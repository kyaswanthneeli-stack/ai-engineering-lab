"""Validate narrow unified-diff input before git apply."""
from pathlib import Path, PurePosixPath
import re
import subprocess

class UnsafePatch(ValueError):
    pass

def validate_patch(patch: str):
    if not patch.endswith("\n") or len(patch)>100_000:
        raise UnsafePatch("Patch must be newline-terminated and under 100 KB")
    if any(marker in patch for marker in ("GIT binary patch","Binary files ")):
        raise UnsafePatch("Binary patches forbidden")
    if re.search(r"(?m)^(?:old mode|new mode|deleted file mode|new file mode|rename from|rename to|copy from|copy to|index )",patch):
        raise UnsafePatch("File metadata edits forbidden")
    headers=re.findall(r"(?m)^diff --git a/(.+?) b/(.+?)$",patch)
    if not headers or len(headers)>20:
        raise UnsafePatch("Expected 1-20 git diff headers")
    for a,b in headers:
        p=PurePosixPath(a)
        if a!=b or not a.endswith(".py") or p.is_absolute() or ".." in p.parts or ".git" in p.parts or "\\" in a or a.startswith("-"):
            raise UnsafePatch("Only existing local Python files may be changed")
    for line in patch.splitlines():
        if line.startswith(("--- ","+++ ")):
            target=line[4:].split("\t",1)[0]
            if target=="/dev/null" or not target.startswith(("a/","b/")):
                raise UnsafePatch("New and deleted files are not permitted")

def apply_patch(repo:Path,patch:str):
    validate_patch(patch)
    for a,_ in re.findall(r"(?m)^diff --git a/(.+?) b/(.+?)$",patch):
        f=repo/a
        if f.is_symlink() or not f.is_file() or not f.resolve().is_relative_to(repo.resolve()):
            raise UnsafePatch("Patch target not an existing regular file")
    process=subprocess.run(["git","apply","--check","-"],input=patch,text=True,cwd=repo,capture_output=True,timeout=10)
    if process.returncode:
        raise UnsafePatch("git apply --check failed")
    process=subprocess.run(["git","apply","-"],input=patch,text=True,cwd=repo,capture_output=True,timeout=10)
    if process.returncode:
        raise UnsafePatch("git apply failed")
