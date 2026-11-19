"""CLI for local read-only indexing, proposed fixes and approved verification."""
import argparse
import json
import os
from pathlib import Path
from .context import index_python
from .planner import propose,save_proposal
from .engine import execute
from .spec import IssueSpec

def main(argv=None):
    parser=argparse.ArgumentParser(prog="repopilot")
    sub=parser.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("index");a.add_argument("repo",type=Path)
    b=sub.add_parser("propose");b.add_argument("repo",type=Path);b.add_argument("issue_file",type=Path)
    b.add_argument("--output",type=Path,default=Path(".runs/proposal.json"))
    c=sub.add_parser("verify");c.add_argument("repo",type=Path);c.add_argument("spec",type=Path)
    c.add_argument("--output",type=Path,default=Path(".runs/verified.json"))
    args=parser.parse_args(argv)
    if args.cmd=="index":
        print(json.dumps([vars(s) for s in index_python(args.repo)],indent=2))
    elif args.cmd=="propose":
        spec,meta=propose(args.repo,args.issue_file.read_text(),os.getenv("REPOPILOT_MODEL",""),os.getenv("REPOPILOT_BASE_URL",""),os.getenv("REPOPILOT_API_KEY"))
        save_proposal(spec,meta,args.output)
        print(json.dumps({"status":"unverified_proposal_saved","path":str(args.output)}))
    else:
        print(json.dumps(execute(args.repo,IssueSpec.from_json(args.spec),args.output),indent=2))
if __name__=="__main__":main()
