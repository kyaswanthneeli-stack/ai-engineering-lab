"""Human-approved draft PR publisher using one atomic Git Data commit.

Never publish without explicit approval. Requires local source equality with
GitHub's default branch before changing the copied repository.
"""
import base64
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.error
import urllib.request
from urllib.parse import quote
from .spec import IssueSpec
from .patches import validate_patch, apply_patch
from .review import review_proposal
from .integrity import proposal_digest
from .test_evidence import check_verification_report
from .workspace import copy_workspace, WorkspaceError

class PublishError(ValueError):
    pass

class GitHubPathNotFound(PublishError):
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
                if len(raw) > 1_000_000:
                    raise PublishError("GitHub response exceeded size limit")
                return json.loads(raw)
        except PublishError:
            raise
        except urllib.error.HTTPError as exc:
            if method == "GET" and exc.code == 404:
                raise GitHubPathNotFound("GitHub resource was not found") from exc
            raise PublishError(f"GitHub request failed ({method} {path.split('?')[0]})") from exc
        except Exception as exc:
            raise PublishError(f"GitHub request failed ({method} {path.split('?')[0]})") from exc

def publish_approved_draft(repo:Path,spec:IssueSpec,verification:dict,remote:str,approval:str,api:GitHubApi=None,repo_subdir:str="")->dict:
    if approval!="I_APPROVE_DRAFT_PR":
        raise PublishError("Explicit human approval is required")
    if review_proposal(spec)["status"]=="blocked":
        raise PublishError("Static proposal review reported blockers; draft PR publishing refused")
    if not isinstance(verification, dict) or verification.get("issue_id")!=spec.issue_id:
        raise PublishError("Issue mismatch")
    if verification.get("proposal_sha256")!=proposal_digest(spec):
        raise PublishError("Verification report does not match exact proposed patch and test")
    try:
        check_verification_report(verification)
    except ValueError as exc:
        raise PublishError("Verified fail-before/pass-after evidence required") from exc
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
        try:
            copy_workspace(repo.resolve(strict=True), root)
        except (WorkspaceError, OSError) as exc:
            raise PublishError("Could not copy a safe publication workspace") from exc
        ref_query = "?ref=" + quote(base_sha, safe="")
        for name in targets:
            local=root/name
            if not local.is_file() or local.is_symlink():
                raise PublishError("Patch target missing")
            remote_file=api.call("GET","/contents/"+quote(remote_path(name),safe="/")+ref_query)
            if remote_file.get("type")!="file" or remote_file.get("encoding")!="base64":
                raise PublishError("Remote file not regular")
            original=base64.b64decode(remote_file["content"])
            if local.read_bytes()!=original:
                raise PublishError("Local source differs from pinned remote base")
        if (root/spec.test_path).exists():
            raise PublishError("Reproduction test path already exists locally")
        try:
            api.call("GET", "/contents/" + quote(remote_path(spec.test_path), safe="/") + ref_query)
        except GitHubPathNotFound:
            pass
        else:
            raise PublishError("Reproduction test path already exists in the remote base commit")
        apply_patch(root,spec.patch)
        branch="repopilot/issue-"+re.sub("[^A-Za-z0-9-]","-",spec.issue_id)[:70]
        branch=branch.rstrip("-")
        # Create one tree and one commit before exposing the branch. Partial
        # per-file uploads cannot leave the review branch half-applied.
        base_commit=api.call("GET","/git/commits/"+base_sha)
        tree_sha=base_commit["tree"]["sha"]
        updates=[
            {"path":remote_path(name),"mode":"100644","type":"blob",
             "content":(root/name).read_text(encoding="utf-8")}
            for name in targets
        ]
        updates.append({"path":remote_path(spec.test_path),"mode":"100644",
                        "type":"blob","content":spec.reproduction_test})
        tree=api.call("POST","/git/trees",{"base_tree":tree_sha,"tree":updates})
        if not isinstance(tree.get("sha"),str):
            raise PublishError("GitHub did not return a tree SHA")
        commit=api.call("POST","/git/commits",{
            "message":"RepoPilot: proposed fix and regression for "+spec.issue_id,
            "tree":tree["sha"],"parents":[base_sha]
        })
        if not isinstance(commit.get("sha"),str):
            raise PublishError("GitHub did not return a commit SHA")
        # A branch collision fails rather than overwriting an existing review.
        api.call("POST","/git/refs",{"ref":"refs/heads/"+branch,"sha":commit["sha"]})
        pr=api.call("POST","/pulls",{
            "title":"[RepoPilot] "+spec.summary[:120],
            "head":branch,"base":default,"draft":True,
            "body":"## Proposed fix\n"+spec.summary[:1000]+"\n\n## Verification\nRegression test failed before the change and passed after the patch in a restricted Docker runner.\n\n**Human review required.** Never merge without inspecting code, security and CI.\n\nIssue: "+spec.issue_id
        })
        return {"draft_pr_created":True,"url":pr.get("html_url"),"number":pr.get("number"),"branch":branch,"commit_sha":commit["sha"]}
