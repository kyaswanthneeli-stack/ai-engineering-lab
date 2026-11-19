"""Explicit, pinned, read-only checkout for a public GitHub repository.

Cloning obtains untrusted source; it does not execute its hooks, install
dependencies or initialize submodules. The returned checkout must only be
tested in the existing restricted sandbox. SHA must be supplied by the user.
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
from pathlib import Path
from .github_issue import ISSUE_URL

COMMIT=re.compile(r"^[0-9a-f]{40}$")

class CheckoutError(ValueError):
    pass

def pinned_checkout(issue_url:str,sha:str,destination:Path,run=subprocess.run)->Path:
    match=ISSUE_URL.fullmatch(issue_url)
    if not match:
        raise CheckoutError("Expected an ordinary public GitHub issue URL")
    if not COMMIT.fullmatch(sha):
        raise CheckoutError("Require full pinned 40-digit lowercase commit SHA")
    if destination.exists():
        raise CheckoutError("Destination must not exist")
    if not shutil.which("git"):
        raise CheckoutError("Git is required")
    owner,repo,_=match.groups()
    url=f"https://github.com/{owner}/{repo}.git"
    destination.parent.mkdir(parents=True,exist_ok=True)
    env={**os.environ,"GIT_TERMINAL_PROMPT":"0",
         "GIT_CONFIG_NOSYSTEM":"1","GIT_CONFIG_GLOBAL":os.devnull}
    commands=[
        ["git","-c","protocol.file.allow=never","init","--template=","--",str(destination)],
        ["git","-C",str(destination),"-c","protocol.file.allow=never","remote","add","origin",url],
        ["git","-C",str(destination),"-c","protocol.file.allow=never","fetch","--depth=1","origin",sha],
        ["git","-C",str(destination),"-c","protocol.file.allow=never","checkout","--detach",sha],
    ]
    try:
        for args in commands:
            p=run(args,env=env,timeout=120,capture_output=True,text=True,check=False)
            if p.returncode:
                raise CheckoutError("Git checkout stage failed; inspect public repository and pinned revision")
    except Exception:
        # Never retain a potentially partial untrusted worktree on failure.
        shutil.rmtree(destination,ignore_errors=True)
        raise
    return destination
