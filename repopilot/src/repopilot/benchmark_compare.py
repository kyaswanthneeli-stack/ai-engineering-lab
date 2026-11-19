"""Strict like-for-like comparison of two official SWE-bench runs.

A result is comparable only if the official harness evaluated the same pinned
instance in BOTH runs. A generated patch or a local Docker pass does not count.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .swebench_export import load_manifest
from .swebench_results import official_summary

_EVALUATED = frozenset({"resolved", "unresolved", "error"})


def _statuses(results_path: Path, predictions_path: Path, selected: set[str]) -> dict[str,str]:
    predictions = [json.loads(s)["instance_id"]
                   for s in predictions_path.read_text(encoding="utf-8").splitlines()
                   if s.strip()]
    submitted = set(predictions)
    raw = json.loads(results_path.read_text(encoding="utf-8"))
    labels = {name:"not_submitted" for name in selected}
    for name in submitted:
        labels[name]="submitted_not_evaluated"
    for field,label in (("resolved_ids","resolved"),("unresolved_ids","unresolved"),
                        ("error_ids","error")):
        for name in raw[field]:
            labels[name]=label
    return labels


def compare_official_runs(manifest:Path, baseline_results:Path,
                          baseline_predictions:Path, candidate_results:Path,
                          candidate_predictions:Path)->dict:
    """Compare official outcomes without assigning a score to untested tasks.

    The shared manifest fixes the denominator. Both result files must be valid
    official harness output; missing/partial evidence fails the comparison.
    """
    selected={task["instance_id"] for task in load_manifest(manifest)}
    baseline=official_summary(manifest,baseline_results,baseline_predictions)
    candidate=official_summary(manifest,candidate_results,candidate_predictions)
    before=_statuses(baseline_results,baseline_predictions,selected)
    after=_statuses(candidate_results,candidate_predictions,selected)
    overlap=sorted(name for name in selected
                   if before[name] in _EVALUATED and after[name] in _EVALUATED)
    newly_resolved=[name for name in overlap
                    if before[name]!="resolved" and after[name]=="resolved"]
    regressed=[name for name in overlap
               if before[name]=="resolved" and after[name]!="resolved"]
    unchanged_resolved=[name for name in overlap
                        if before[name]=="resolved" and after[name]=="resolved"]
    return {
        "selected_tasks":len(selected),
        "baseline_submitted":baseline["submitted"],
        "baseline_officially_evaluated":baseline["evaluated"],
        "baseline_resolved":baseline["resolved"],
        "candidate_submitted":candidate["submitted"],
        "candidate_officially_evaluated":candidate["evaluated"],
        "candidate_resolved":candidate["resolved"],
        "comparable_officially_evaluated":len(overlap),
        "baseline_resolved_on_comparable":sum(before[n]=="resolved" for n in overlap),
        "candidate_resolved_on_comparable":sum(after[n]=="resolved" for n in overlap),
        "resolved_delta_on_comparable":(
            sum(after[n]=="resolved" for n in overlap)-
            sum(before[n]=="resolved" for n in overlap)) if overlap else None,
        "newly_resolved":newly_resolved,
        "regressed":regressed,
        "unchanged_resolved":unchanged_resolved,
        "per_task":[{"instance_id":n,"baseline":before[n],
                     "candidate":after[n],
                     "directly_comparable":n in overlap}
                    for n in sorted(selected)],
        "scope":"Official SWE-bench harness outcomes only. A missing model patch "
                "or unreported evaluator result is never a solved issue. "
                "Resolution deltas use only identical evaluated instance IDs."
    }


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("manifest",type=Path)
    parser.add_argument("baseline_results",type=Path)
    parser.add_argument("baseline_predictions",type=Path)
    parser.add_argument("candidate_results",type=Path)
    parser.add_argument("candidate_predictions",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args(argv)
    result=compare_official_runs(
        args.manifest,args.baseline_results,args.baseline_predictions,
        args.candidate_results,args.candidate_predictions)
    data=json.dumps(result,indent=2)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(data,encoding="utf-8")
    print(data,end="")


if __name__=="__main__":
    main()
