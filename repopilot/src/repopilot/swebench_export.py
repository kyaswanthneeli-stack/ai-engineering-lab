"""Prepare SWE-bench Lite predictions for the official evaluator.

This module NEVER produces evaluation scores. An entry is exported only when an
actual model-generated patch file and metadata are present for a pinned task.
No patch means no prediction (not a solved issue).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE = re.compile(r"^[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+-[0-9]+$")


def load_manifest(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not 10 <= len(tasks) <= 20:
        raise ValueError("Expected a pinned 10–20 task benchmark manifest")
    ids = [item.get("instance_id") for item in tasks]
    if len(ids) != len(set(ids)) or not all(isinstance(i, str) and INSTANCE.fullmatch(i) for i in ids):
        raise ValueError("Invalid or duplicate benchmark instance identifiers")
    for task in tasks:
        if not isinstance(task.get("base_commit"), str) or not re.fullmatch(r"[a-f0-9]{40}", task["base_commit"]):
            raise ValueError("Each task requires an exact 40-character base commit")
    return tasks


def export_predictions(manifest: Path, submissions: Path, output: Path) -> dict:
    """Export only reviewed, model-generated patches from an explicit manifest.

    Required submission JSON per task:
      instance_id, base_commit, model_name_or_path, model_patch,
      generated_by_model=true, human_reviewed=true.
    These attestations are input declarations, not independently verified.
    Run the official SWE-bench harness to obtain authoritative outcomes.
    """
    tasks = load_manifest(manifest)
    result = []
    missing = []
    for task in tasks:
        instance_id = task["instance_id"]
        path = submissions / (instance_id + ".json")
        if not path.exists():
            missing.append(instance_id)
            continue
        item = json.loads(path.read_text(encoding="utf-8"))
        if (item.get("instance_id") != instance_id or
                item.get("base_commit") != task["base_commit"] or
                item.get("generated_by_model") is not True or
                item.get("human_reviewed") is not True):
            raise ValueError("Missing model/reviewer attestations or base commit mismatch: " + instance_id)
        model = item.get("model_name_or_path")
        patch = item.get("model_patch")
        if not isinstance(model, str) or not 1 <= len(model) <= 120:
            raise ValueError("Invalid model name: " + instance_id)
        if not isinstance(patch, str) or not 10 <= len(patch) <= 300000:
            raise ValueError("Invalid nonempty model patch: " + instance_id)
        if "diff --git a/" not in patch or not patch.endswith("\n"):
            raise ValueError("Expected a git-style patch ending with newline: " + instance_id)
        result.append({"instance_id": instance_id, "model_name_or_path": model, "model_patch": patch})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in result), encoding="utf-8")
    return {
        "dataset": "princeton-nlp/SWE-bench_Lite",
        "selected_tasks": len(tasks),
        "submitted_predictions": len(result),
        "unsubmitted_tasks": len(missing),
        "missing_instance_ids": missing,
        "status": "predictions_exported_not_evaluated" if result else "no_model_predictions_submitted",
        "official_resolution_rate": None,
        "warning": "A submitted patch is not a resolved issue. Run the official SWE-bench harness and inspect results.json and per-instance report.json."
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export real model predictions without claiming evaluation")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("submissions", type=Path)
    parser.add_argument("--output", type=Path, default=Path(".runs/swebench-predictions.jsonl"))
    args = parser.parse_args(argv)
    print(json.dumps(export_predictions(args.manifest, args.submissions, args.output), indent=2))


if __name__ == "__main__":
    main()
