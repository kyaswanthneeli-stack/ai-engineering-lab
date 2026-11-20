"""Issue URL -> model proposal -> Docker verification -> offline evidence.
No pull-request side effects occur here.
"""
from pathlib import Path
from dataclasses import replace
import json
import os
import time
from .github_issue import fetch_public_issue
from .planner import propose, save_proposal
from .engine import execute
from .dashboard import render_dashboard
from .review import review_proposal

def run_issue(repo:Path,issue_url:str,output:Path,issue_reader=fetch_public_issue,model_proposer=propose,verifier=execute)->dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be empty; history is immutable per run")
    output.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    events=[]
    def record(event,detail):
        events.append({"step":event,"detail":detail,"elapsed_ms":round((time.monotonic()-start)*1000)})
    report=None
    proposal_data=None
    issue_data=None
    try:
        issue_data=issue_reader(issue_url)
        record("issue_fetched",issue_data["issue_id"])
        spec,meta=model_proposer(repo,issue_data["text"],os.environ.get("REPOPILOT_MODEL",""),os.environ.get("REPOPILOT_BASE_URL",""),os.environ.get("REPOPILOT_API_KEY"))
        record("model_proposal_received",meta.get("model","unspecified"))
        static_review=review_proposal(spec)
        record("static_proposal_review",static_review["status"])
        if static_review["status"]=="blocked":
            raise ValueError("Proposal rejected by static safety review; inspect details before retrying")
        # Bind proposal to the authenticated issue identifier, not model-authored text.
        spec=replace(spec,issue_id=issue_data["issue_id"])
        save_proposal(spec,meta,output/"proposal.json")
        proposal_data=json.loads((output/"proposal.json").read_text())
        record("proposal_saved_for_human_review","Generated changes are never pushed automatically")
        report=verifier(repo,spec,output/"verification.json")
        record("docker_verification_complete",report["outcome"])
        report["model_generated_proposal"]=True
        report["model_metadata"]=meta
        report["static_review"]=static_review
    except Exception as exc:
        record("pipeline_failed",type(exc).__name__)
        report=report or {"issue_id":(issue_data or {}).get("issue_id","unknown"),"outcome":"failed","model_generated_proposal":bool(proposal_data),"error_type":type(exc).__name__,"error":"Pipeline failed; consult the sanitized error type and CI checks","draft_pr_created":False}
    report["events"]=events
    report["elapsed_ms"]=round((time.monotonic()-start)*1000)
    (output/"run.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    if issue_data:
        (output/"issue.json").write_text(json.dumps(issue_data,indent=2)+"\n",encoding="utf-8")
    render_dashboard(report,output/"dashboard.html",proposal=proposal_data,issue=issue_data)
    return report
