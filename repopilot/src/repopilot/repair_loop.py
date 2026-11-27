"""Bounded issue-proposal-verification loop, retaining every attempt.

This is a controlled repair loop, not unbounded recursive autonomy.
Model output remains subject to static checks and sandbox verification.
"""
from __future__ import annotations
from dataclasses import replace
import json
import hashlib
import os
import time
from pathlib import Path
from .dashboard import render_dashboard
from .engine import execute
from .github_issue import fetch_public_issue
from .planner import propose,save_proposal
from .review import review_proposal
from .security import redact_secrets


def run_with_repair(repo:Path,issue_url:str,output:Path,*,max_attempts:int=3,
                    issue_reader=fetch_public_issue,model_proposer=propose,
                    verifier=execute)->dict:
    if not 1<=max_attempts<=3:
        raise ValueError("Only 1–3 attempts permitted")
    if output.exists():
        raise ValueError("Output directory already exists; evidence is immutable")
    output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    report={"outcome":"failed","issue_url":issue_url,"attempts":[],"draft_pr_created":False,
            "model_generated_proposal":False}
    issue=None
    last_proposal=None
    feedback=""
    seen_proposals=set()
    # A changed reproduction test cannot make an already-failed source patch new.
    # Only track patches that actually reached the sandbox verifier.
    verified_attempt_patches=set()
    def test_feedback(path:Path)->str:
        # Preserve useful failure signals, without copying an entire untrusted test log.
        if not path.is_file():
            return ""
        try:
            record=json.loads(path.read_text(encoding="utf-8"))
            if record.get("outcome")!="failed":
                return ""
            stage=record.get("failed_stage","unknown")
            after=record.get("after",{}) or {}
            text=redact_secrets(str(after.get("output","")))[-1200:]
            return f"Failed verification stage: {stage}. Test exit={after.get('exit_code')}. Test output excerpt:\\n{text}"
        except (ValueError,TypeError,OSError):
            return ""
    try:
        issue=issue_reader(issue_url)
        report["issue_id"]=issue["issue_id"]
        (output/"issue.json").write_text(json.dumps(issue,indent=2)+"\n",encoding="utf-8")
        for number in range(1,max_attempts+1):
            record={"number":number,"status":"started"}
            report["attempts"].append(record)
            prompt=issue["text"]
            if feedback:
                prompt += ("\n\nPREVIOUS ATTEMPT FAILED (untrusted local error summary):\n"
                           + feedback[:700]
                           +"\nGenerate a corrected proposal. Never assume tests passed.")
            try:
                spec,meta=model_proposer(repo,prompt,
                    os.getenv("REPOPILOT_MODEL",""),
                    os.getenv("REPOPILOT_BASE_URL",""),
                    os.getenv("REPOPILOT_API_KEY"))
                spec=replace(spec,issue_id=issue["issue_id"])
                report["model_generated_proposal"]=True
                record["provider_model"]=meta.get("model","unknown")
                record["provider_usage"]=meta.get("provider_reported_usage_by_attempt",[])
                record["status"]="proposed"
                # A repeated proposal after failed verification adds no new
                # information and can waste a paid model call or sandbox run.
                # Keep it as evidence, but do not execute the same patch twice.
                fingerprint=hashlib.sha256(
                    json.dumps({"patch":spec.patch,
                                "test_path":spec.test_path,
                                "reproduction_test":spec.reproduction_test,
                                "test_command":spec.test_command},
                               sort_keys=True).encode("utf-8")
                ).hexdigest()
                record["proposal_sha256"]=fingerprint
                patch_sha256=hashlib.sha256(spec.patch.encode("utf-8")).hexdigest()
                record["patch_sha256"]=patch_sha256
                repeated=fingerprint in seen_proposals
                seen_proposals.add(fingerprint)
                file=output/f"attempt-{number:02d}-proposal.json"
                save_proposal(spec,meta,file)
                last_proposal=json.loads(file.read_text(encoding="utf-8"))
                if repeated:
                    record["duplicate_proposal"]=True
                    raise ValueError("Duplicate proposal: model repeated an already-attempted patch and test")
                if patch_sha256 in verified_attempt_patches:
                    record["duplicate_failed_patch"]=True
                    raise ValueError("Source patch already failed sandbox verification")
                review=review_proposal(spec)
                record["review"]=review
                if review["status"]=="blocked":
                    raise ValueError("Proposed test or patch failed static review")
                verified_attempt_patches.add(patch_sha256)
                verification=verifier(repo,spec,output/f"attempt-{number:02d}-verification.json")
                if (verification.get("outcome")!="verified_in_sandbox" or
                    verification.get("baseline",{}).get("exit_code")!=0 or
                    verification.get("before",{}).get("exit_code") in (0,None) or
                    verification.get("after",{}).get("exit_code")!=0):
                    raise ValueError("Verifier did not return complete passing evidence")
                record["status"]="verified"
                record["elapsed_ms"]=verification.get("elapsed_ms")
                report.update(verification)
                report["outcome"]="verified_in_sandbox"
                report["successful_attempt"]=number
                break
            except Exception as exc:
                record["status"]="failed"
                record["error_type"]=type(exc).__name__
                # Avoid echoing secret-bearing model outputs or raw source in traces.
                evidence=test_feedback(output/f"attempt-{number:02d}-verification.json")
                feedback=(evidence or (type(exc).__name__+": candidate rejected or failed verification"))[:1500]
                if record.get("duplicate_failed_patch"):
                    feedback="The same source patch already failed sandbox verification. Change the source fix, not only the reproduction test."
                elif record.get("duplicate_proposal"):
                    feedback="Repeated an already-rejected patch and reproduction test. Propose materially different source and test changes."
                record["error_summary"]=type(exc).__name__+": candidate rejected or failed verification"
                record["has_test_failure_evidence"]=bool(evidence)
    except Exception as exc:
        report["setup_error_type"]=type(exc).__name__
        report["setup_error"]="Could not retrieve or validate public issue"
    report["elapsed_ms"]=round((time.monotonic()-started)*1000)
    (output/"run.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    render_dashboard(report,output/"dashboard.html",last_proposal,issue)
    return report
