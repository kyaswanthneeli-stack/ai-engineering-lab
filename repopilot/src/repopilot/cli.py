"""CLI for local read-only indexing, proposed fixes and approved verification."""
import argparse
import json
import os
from pathlib import Path
from .context import index_python
from .planner import propose,save_proposal
from .engine import execute
from .spec import IssueSpec
from .pipeline import run_issue
from .dashboard import render_dashboard
from .benchmark import read_and_aggregate
from .pr import publish_approved_draft
from .swebench import write_manifest

def main(argv=None):
    parser=argparse.ArgumentParser(prog="repopilot")
    sub=parser.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("index");a.add_argument("repo",type=Path)
    b=sub.add_parser("propose");b.add_argument("repo",type=Path);b.add_argument("issue_file",type=Path)
    b.add_argument("--output",type=Path,default=Path(".runs/proposal.json"))
    c=sub.add_parser("verify");c.add_argument("repo",type=Path);c.add_argument("spec",type=Path)
    c.add_argument("--output",type=Path,default=Path(".runs/verified.json"))
    d=sub.add_parser("run",help="Fetch a GitHub issue, request a model patch and verify in Docker")
    d.add_argument("repo",type=Path);d.add_argument("issue_url")
    d.add_argument("--output",type=Path,default=Path(".runs/agent-run"))
    e=sub.add_parser("dashboard",help="Render offline evidence from a verification report")
    e.add_argument("report",type=Path)
    e.add_argument("--output",type=Path,default=Path(".runs/dashboard.html"))
    f=sub.add_parser("benchmark",help="Aggregate real run records, not fabricated scores")
    f.add_argument("reports",nargs="*",type=Path)
    f.add_argument("--dataset",default="unlabeled")
    g=sub.add_parser("draft-pr",help="Publish only after human review and explicit approval")
    g.add_argument("repo",type=Path);g.add_argument("proposal",type=Path);g.add_argument("report",type=Path)
    g.add_argument("--remote",required=True)
    g.add_argument("--approve",default="",help="Must be exactly I_APPROVE_DRAFT_PR")
    h=sub.add_parser("select-swebench",help="Create 12-task public SWE-bench Lite manifest; no score computed")
    h.add_argument("--limit",type=int,default=12)
    h.add_argument("--seed",type=int,default=73)
    h.add_argument("--output",type=Path,default=Path(".runs/swebench-lite-manifest.json"))
    args=parser.parse_args(argv)
    if args.cmd=="index":
        print(json.dumps([vars(s) for s in index_python(args.repo)],indent=2))
    elif args.cmd=="propose":
        spec,meta=propose(args.repo,args.issue_file.read_text(),os.getenv("REPOPILOT_MODEL",""),os.getenv("REPOPILOT_BASE_URL",""),os.getenv("REPOPILOT_API_KEY"))
        save_proposal(spec,meta,args.output)
        print(json.dumps({"status":"unverified_proposal_saved","path":str(args.output)}))
    elif args.cmd=="verify":
        print(json.dumps(execute(args.repo,IssueSpec.from_json(args.spec),args.output),indent=2))
    elif args.cmd=="run":
        result=run_issue(args.repo,args.issue_url,args.output)
        print(json.dumps({"outcome":result["outcome"],"output":str(args.output),"dashboard":str(args.output/"dashboard.html")},indent=2))
        if result["outcome"]!="verified_in_sandbox":
            raise SystemExit(1)
    elif args.cmd=="dashboard":
        report=json.loads(args.report.read_text(encoding="utf-8"))
        print(render_dashboard(report,args.output))
    elif args.cmd=="benchmark":
        print(json.dumps(read_and_aggregate(args.reports,args.dataset),indent=2))
    elif args.cmd=="select-swebench":
        print(json.dumps(write_manifest(args.output,args.limit,args.seed),indent=2))
    elif args.cmd=="draft-pr":
        report=json.loads(args.report.read_text(encoding="utf-8"))
        result=publish_approved_draft(args.repo,IssueSpec.from_json(args.proposal),report,args.remote,args.approve)
        print(json.dumps(result,indent=2))
if __name__=="__main__":main()
