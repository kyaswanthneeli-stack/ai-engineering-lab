"""Run each pinned SWE-bench Lite task with a bounded real model attempt.

This module collects predictions but does NOT evaluate them. Only model-generated
patches are exported; missing and timed-out tasks remain explicitly unresolved
and unscored until the official SWE-bench harness is run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from .swebench_export import load_manifest


def collect(manifest: Path, output: Path, *, per_task_timeout: int = 240,
            max_steps: int = 10, instance_ids: list[str] | None = None) -> dict:
    if not 30 <= per_task_timeout <= 900 or not 2 <= max_steps <= 24:
        raise ValueError("Timeout or agent steps outside safe bounds")
    manifest_tasks = load_manifest(manifest)  # Original 10-20 task safety gate stays intact.
    tasks = manifest_tasks
    if instance_ids is not None:
        allowed = {task["instance_id"] for task in manifest_tasks}
        if (not isinstance(instance_ids, list) or not 1 <= len(instance_ids) <= 20 or
                len(set(instance_ids)) != len(instance_ids) or
                not set(instance_ids) <= allowed):
            raise ValueError("Pilot tasks must be unique nonempty IDs from pinned manifest")
        selected = set(instance_ids)
        tasks = [task for task in manifest_tasks if task["instance_id"] in selected]
    if output.exists():
        raise ValueError("Refuse to overwrite existing evaluation evidence")
    output.mkdir(parents=True)
    predictions = []
    records = []
    for index, task in enumerate(tasks, 1):
        instance_id = task["instance_id"]
        task_output = output / "attempts" / instance_id
        task_output.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        command = [sys.executable, "-m", "repopilot.benchmark_attempt",
                   instance_id, "--agentic", "--max-steps", str(max_steps),
                   "--manifest", str(manifest), "--output", str(task_output)]
        try:
            subprocess.run(command, timeout=per_task_timeout,
                           capture_output=True, check=False)
            if not (task_output / "attempt.json").is_file():
                report = {"status": "attempt_failed_without_evidence",
                          "error_type": "MissingAttemptRecord"}
            else:
                report = json.loads((task_output / "attempt.json").read_text())
        except subprocess.TimeoutExpired:
            report = {"status": "model_timeout",
                      "error_type": "BoundedTaskTimeout"}
        except OSError:
            report = {"status": "execution_failed",
                      "error_type": "ProcessLaunchFailure"}
        record = {"instance_id": instance_id, "repo": task["repo"],
                  "base_commit": task["base_commit"],
                  "status": report.get("status", "unknown"),
                  "error_type": report.get("error_type"),
                  "elapsed_ms": round((time.monotonic()-started)*1000),
                  "officially_evaluated": False, "officially_resolved": None}
        if report.get("status") == "model_patch_proposed":
            file = task_output / "unreviewed-prediction.json"
            if file.is_file():
                proposal = json.loads(file.read_text())
                patch = proposal.get("model_patch")
                model = proposal.get("model_name_or_path")
                if (proposal.get("instance_id") == instance_id and
                    proposal.get("base_commit") == task["base_commit"] and
                    proposal.get("generated_by_model") is True and
                    isinstance(model, str) and bool(model) and
                    isinstance(patch, str) and patch.startswith("diff --git a/") and
                    patch.endswith("\n")):
                    predictions.append({"instance_id": instance_id,
                                        "model_name_or_path": model,
                                        "model_patch": patch})
                    record["prediction_exported"] = True
                else:
                    record["status"] = "invalid_model_prediction"
            else:
                record["status"] = "missing_model_prediction"
        records.append(record)
        print(f"[{index}/{len(tasks)}] {instance_id}: {record['status']}",
              flush=True)
        (output / "progress.json").write_text(
            json.dumps(records, indent=2) + "\n")
    (output / "predictions.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False)+"\n" for x in predictions))
    summary = {"dataset": "princeton-nlp/SWE-bench_Lite",
               "pinned_manifest_tasks": len(manifest_tasks),
               "selected_tasks": len(tasks),
               "model_predictions": len(predictions),
               "missing_predictions": len(tasks)-len(predictions),
               "officially_evaluated": False,
               "officially_resolved": None,
               "status": ("predictions_ready_unscored" if predictions else
                          "no_valid_model_predictions_unscored"),
               "tasks": records}
    (output / "summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path,
                        default=Path("benchmarks/swebench-lite-12.json"))
    parser.add_argument("--output", type=Path,
                        default=Path(".runs/swebench-batch"))
    parser.add_argument("--per-task-timeout", type=int, default=240)
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--instance-ids", nargs="+",
                        help="Optional unique subset of the original pinned manifest")
    args = parser.parse_args(argv)
    summary = collect(args.manifest, args.output,
                      per_task_timeout=args.per_task_timeout,
                      max_steps=args.max_steps, instance_ids=args.instance_ids)
    print(json.dumps({k: v for k, v in summary.items() if k != "tasks"}, indent=2))


if __name__ == "__main__":
    main()
