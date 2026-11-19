"""Convert a single malformed model hunk into a canonical diff when unambiguous.

This is a formatting repair, not a semantic patch writer: exact model-supplied
deleted lines must appear as a unique contiguous block in the original file.
"""
import difflib
from pathlib import Path
from .patches import validate_patch,UnsafePatch

class PatchRepairError(ValueError):
    pass

def reconstruct_single_hunk(repo:Path,patch:str)->str:
    validate_patch(patch)
    lines=patch.splitlines()
    headers=[line for line in lines if line.startswith("diff --git ")]
    hunks=[i for i,line in enumerate(lines) if line.startswith("@@ ")]
    if len(headers)!=1 or len(hunks)!=1:
        raise PatchRepairError("Only one-file, one-hunk patch normalization is supported")
    from .pr import patch_targets
    names=patch_targets(patch)
    if len(names)!=1:
        raise PatchRepairError("One file must be modified")
    name=names[0]
    root=repo.resolve(strict=True)
    target=root/name
    if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(root):
        raise PatchRepairError("Target must be an existing local Python file")
    if target.stat().st_size>200_000:
        raise PatchRepairError("Target exceeds patch-repair size limit")
    changed=lines[hunks[0]+1:]
    removed=[]
    inserted=[]
    for line in changed:
        if line.startswith("-"):
            removed.append(line[1:])
        elif line.startswith("+"):
            inserted.append(line[1:])
        elif line.startswith(" ") or line.startswith("\\ No newline at end of file"):
            continue
        else:
            raise PatchRepairError("Unrecognized diff hunk line")
    if not removed or not inserted or len(removed)>35 or len(inserted)>35:
        raise PatchRepairError("A bounded replacement block is required")
    source=target.read_text(encoding="utf-8")
    if not source.endswith("\n"):
        raise PatchRepairError("Only newline-terminated Python source supported")
    original=source.splitlines(keepends=True)
    stripped=[line.rstrip("\r\n") for line in original]
    matches=[i for i in range(len(stripped)-len(removed)+1) if stripped[i:i+len(removed)]==removed]
    if len(matches)!=1:
        raise PatchRepairError("Model-deleted lines must match exactly once in source")
    at=matches[0]
    result=original[:at]+[line+"\n" for line in inserted]+original[at+len(removed):]
    if result==original:
        raise PatchRepairError("Patch made no change")
    unified="".join(difflib.unified_diff(original,result,fromfile="a/"+name,tofile="b/"+name))
    if not unified:
        raise PatchRepairError("Diff reconstruction produced no changes")
    candidate=f"diff --git a/{name} b/{name}\n"+unified
    validate_patch(candidate)
    return candidate
