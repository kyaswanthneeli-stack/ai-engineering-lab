"""Attempt exactly one public SWE-bench Lite task without claiming resolution.

Loads the official task statement, checks out the pinned upstream commit, and
asks the configured model to propose a patch. The proposal is *not evaluated*
or submitted as a benchmark success. No target-repository code is executed.

The current Python-only model planner is deliberately limited; many tasks will
fail to produce a valid patch. Failures are first-class recorded outcomes.
"""
from __future__ import annotations

import argparse
from functools import partial
import json
import os
from pathlib import Path
import re
import tempfile
import time
from .checkout import pinned_checkout
from .benchmark_planner import propose_benchmark
from .swebench_export import load_manifest

REPO=re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

def attempt_one(manifest:Path,instance_id:str,output:Path,*,dataset_loader=None,
                checkout=pinned_checkout,model_proposer=propose_benchmark,model=None,url=None,token=None)->dict:
    tasks={t["instance_id"]:t for t in load_manifest(manifest)}
    if instance_id not in tasks:
        raise ValueError("Instance ID is not in the pinned manifest")
    task=tasks[instance_id]
    if not REPO.fullmatch(task["repo"]):
        raise ValueError("Invalid upstream repository name")
    if output.exists():
        raise ValueError("Output already exists; refuse to overwrite evidence")
    output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    report={"instance_id":instance_id,"repo":task["repo"],"base_commit":task["base_commit"],
            "status":"not_attempted","officially_evaluated":False,"officially_resolved":None,
            "is_reference_patch":False}
    try:
        if dataset_loader is None:
            try:
                from datasets import load_dataset
            except ImportError as exc:
                raise RuntimeError("Install datasets optional dependency") from exc
            dataset=load_dataset("princeton-nlp/SWE-bench_Lite",split="test")
        else:
            dataset=dataset_loader()
        matches=[row for row in dataset if row["instance_id"]==instance_id]
        if len(matches)!=1:
            raise ValueError("Official dataset row missing or duplicated")
        row=matches[0]
        if row["base_commit"]!=task["base_commit"] or row["repo"]!=task["repo"]:
            raise ValueError("Pinned commit/repository does not match official dataset")
        issue=row["problem_statement"]
        if not isinstance(issue,str) or not issue.strip():
            raise ValueError("Official issue statement missing")
        report["status"]="attempted"
        owner,repo=task["repo"].split("/")
        with tempfile.TemporaryDirectory(prefix="repopilot-swebench-") as tmp:
            # Checkout helper only parses the URL to derive the public repo;
            # the issue statement is read from the official pinned dataset.
            work=checkout(f"https://github.com/{owner}/{repo}/issues/1",
                          task["base_commit"],Path(tmp)/"repo")
            spec,meta=model_proposer(work,issue[:12000],
                                     model or os.getenv("REPOPILOT_MODEL",""),
                                     url or os.getenv("REPOPILOT_BASE_URL",""),
                                     token if token is not None else os.getenv("REPOPILOT_API_KEY"))
        report["model"]=meta.get("model","")
        report["agent_steps"]=meta.get("agent_steps")
        report["inspected_files"]=meta.get("inspected_files",[])
        report["tool_trace"]=meta.get("tool_trace",[])
        report["provider_usage"]=meta.get("provider_reported_usage_by_attempt",[])
        report["status"]="model_patch_proposed"
        report["model_generated"]=True
        # Model-reported provenance does not replace review or the official harness.
        submission={"instance_id":instance_id,"base_commit":task["base_commit"],
                    "model_name_or_path":meta["model"],"model_patch":spec.patch,
                    "generated_by_model":True,"human_reviewed":False}
        (output/"unreviewed-prediction.json").write_text(
            json.dumps(submission,indent=2)+"\n",encoding="utf-8")
    except Exception as exc:
        report["status"]="failed_model_attempt" if report["status"]=="attempted" else "setup_failed"
        report["error_type"]=type(exc).__name__
        report["error"]=str(exc)[:350]
    report["elapsed_ms"]=round((time.monotonic()-started)*1000)
    (output/"attempt.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("instance_id")
    parser.add_argument("--manifest",type=Path,default=Path("benchmarks/swebench-lite-12.json"))
    parser.add_argument("--output",type=Path,default=Path(".runs/swebench-attempt"))
    parser.add_argument("--agentic",action="store_true",help="Enable bounded model-directed read-only tool calls")
    parser.add_argument("--max-steps",type=int,default=18,help="Bounded tool-agent model calls (2–24)")
    args=parser.parse_args(argv)
    if args.agentic:
        if not 2<=args.max_steps<=24:
            parser.error("--max-steps must be between 2 and 24")
        from .agentic_benchmark import propose_agentic_benchmark
        planner=partial(propose_agentic_benchmark,max_steps=args.max_steps,
                        auto_issue_paths=True)
    else:
        planner=propose_benchmark
    result=attempt_one(args.manifest,args.instance_id,args.output,model_proposer=planner)
    print(json.dumps(result,indent=2))
    if result["status"]!="model_patch_proposed":
        raise SystemExit(1)

if __name__=="__main__":
    main()
