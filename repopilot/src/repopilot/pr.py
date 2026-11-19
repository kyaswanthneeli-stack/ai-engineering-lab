"""Human-approved draft PR publisher, using GitHub Contents API.

Never publish without explicit approval. Requires local source equality with
GitHub's default branch before changing the copied repository.
"""
import base64
import json
import os
from pathlib import Path
import re
import tempfile
import shutil
import urllib.request
from urllib.parse import quote
from .spec import IssueSpec
from .patches import validate_patch, apply_patch
from .review import review_proposal

class PublishError(ValueError):
    pass

def patch_targets(patch:str)->list[str]:
    validate_patch(patch)
    return re.findall(r"(?m)^diff --git a/(.+?) b/\1$",patch)

class _RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise PublishError("GitHub API redirects rejected")

class GitHubApi:
    def __init__(self, token:str, repo:str):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repo):
            raise PublishError("Invalid repository name")
        if not token:
            raise PublishError("GITHUB_TOKEN required")
        self.repo=repo
        self.base=f"https://api.github.com/repos/{repo}"
        self.token=token
    def call(self,method:str,path:str,data=None):
        if (path and not path.startswith("/")) or "://" in path:
            raise PublishError("Invalid GitHub API path")
        payload=json.dumps(data).encode() if data is not None else None
        request=urllib.request.Request(self.base+path,data=payload,method=method,headers={
            "Accept":"application/vnd.github+json",
            "Authorization":"Bearer "+self.token,
            "Content-Type":"application/json",
            "User-Agent":"RepoPilot/0.3"
        })
        try:
            opener=urllib.request.build_opener(_RejectRedirect())
            with opener.open(request,timeout=20) as response:
                raw=response.read(1_000_001)
                return json.loads(raw)
        except Exception as exc:
            raise PublishError(f"GitHub request failed ({method} {path.split('?')[0]})") from exc

def publish_approved_draft(repo:Path,spec:IssueSpec,verification:dict,remote:str,approval:str,api:GitHubApi=None,repo_subdir:str="")->dict:
    if approval!="I_APPROVE_DRAFT_PR":
        raise PublishError("Explicit human approval is required")
    if review_proposal(spec)["status"]=="blocked":
        raise PublishError("Static proposal review reported blockers; draft PR publishing refused")
    if verification.get("outcome")!="verified_in_sandbox" or verification.get("baseline",{}).get("exit_code")!=0 or verification.get("before",{}).get("exit_code") in (None,0) or verification.get("after",{}).get("exit_code")!=0:
        raise PublishError("Verified fail-before/pass-after evidence required")
    if verification.get("issue_id")!=spec.issue_id:
        raise PublishError("Issue mismatch")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",remote):
        raise PublishError("Invalid remote")
    if not spec.issue_id.startswith(remote+"#"):
        raise PublishError("Issue must belong to target repository")
    targets=patch_targets(spec.patch)
    if repo_subdir:
        from pathlib import PurePosixPath
        prefix=PurePosixPath(repo_subdir)
        if prefix.is_absolute() or ".." in prefix.parts or "\\\\" in repo_subdir:
            raise PublishError("Unsafe source subdirectory")
        repo_subdir=prefix.as_posix().strip("/")
    def remote_path(name):
        return (repo_subdir+"/"+name) if repo_subdir else name
    if len(targets)>10:
        raise PublishError("Too many files")
    if api is None:
        api=GitHubApi(os.getenv("GITHUB_TOKEN",""),remote)
    identity=api.call("GET","")
    if identity.get("full_name")!=remote:
        raise PublishError("Repository identity mismatch")
    default=identity.get("default_branch")
    if not isinstance(default,str) or not re.fullmatch(r"[A-Za-z0-9_.-]+",default):
        raise PublishError("Unsupported default branch")
    branch_info=api.call("GET","/git/ref/heads/"+default)
    base_sha=branch_info["object"]["sha"]
    with tempfile.TemporaryDirectory(prefix="repopilot-pr-") as td:
        root=Path(td)/"repo"
        shutil.copytree(repo.resolve(strict=True),root,ignore=shutil.ignore_patterns(".git",".venv","__pycache__",".runs"),symlinks=True)
        # Reject symlinks before using the copy
        if any(p.is_symlink() for p in root.rglob("*")):
            raise PublishError("Symlinks are forbidden")
        originals={}
        for name in targets:
            local=root/name
            if not local.is_file() or local.is_symlink():
                raise PublishError("Patch target missing")
            remote_file=api.call("GET","/contents/"+quote(remote_path(name),safe="/")+"?ref="+quote(default,safe=""))
            if remote_file.get("type")!="file" or remote_file.get("encoding")!="base64":
                raise PublishError("Remote file not regular")
            original=base64.b64decode(remote_file["content"])
            if local.read_bytes()!=original:
                raise PublishError("Local source differs from remote default branch")
            originals[name]=remote_file["sha"]
        if (root/spec.test_path).exists():
            raise PublishError("Reproduction test path already exists locally")
        apply_patch(root,spec.patch)
        branch="repopilot/issue-"+re.sub("[^A-Za-z0-9-]","-",spec.issue_id)[:70]
        branch=branch.rstrip("-")
        # A branch already present causes a GitHub conflict rather than overwrite.
        api.call("POST","/git/refs",{"ref":"refs/heads/"+branch,"sha":base_sha})
        for name in targets:
            api.call("PUT","/contents/"+quote(remote_path(name),safe="/"),{
                "message":"RepoPilot: proposed fix for "+spec.issue_id,
                "content":base64.b64encode((root/name).read_bytes()).decode(),
                "sha":originals[name],"branch":branch
            })
        api.call("PUT","/contents/"+quote(remote_path(spec.test_path),safe="/"),{
            "message":"RepoPilot: regression test for "+spec.issue_id,
            "content":base64.b64encode(spec.reproduction_test.encode()).decode(),"branch":branch
        })
        pr=api.call("POST","/pulls",{
            "title":"[RepoPilot] "+spec.summary[:120],
            "head":branch,"base":default,"draft":True,
            "body":"## Proposed fix\n"+spec.summary[:1000]+"\n\n## Verification\nRegression test failed before the change and passed after the patch in a restricted Docker runner.\n\n**Human review required.** Never merge without inspecting code, security and CI.\n\nIssue: "+spec.issue_id
        })
        return {"draft_pr_created":True,"url":pr.get("html_url"),"number":pr.get("number"),"branch":branch}
