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


_ALLOWED_PROGRESS_STAGES=frozenset({
    "initialized", "dataset_verified", "pinned_checkout_complete",
    "model_response_received",
})


def _read_stage(task_output:Path,instance_id:str)->dict:
    """Read trusted local diagnostic metadata, never source/model responses."""
    path=task_output/"stage.json"
    try:
        if not path.is_file() or path.stat().st_size>4096:
            return {}
        item=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError,TypeError,UnicodeError):
        return {}
    if (not isinstance(item,dict) or item.get("instance_id")!=instance_id
            or item.get("last_completed_stage") not in _ALLOWED_PROGRESS_STAGES
            or item.get("officially_evaluated") is not False):
        return {}
    elapsed=item.get("stage_elapsed_ms")
    if type(elapsed) is not int or elapsed<0:
        return {}
    return {"last_completed_stage":item["last_completed_stage"],
            "stage_elapsed_ms":elapsed}


_RETRYABLE_STATUSES = frozenset({
    "model_timeout", "provider_unavailable", "failed_model_attempt",
    "attempt_failed_without_evidence", "execution_failed",
    "invalid_model_prediction", "missing_model_prediction", "setup_failed",
})


def retryable_task_ids(manifest_tasks: list[dict], previous: Path) -> list[str]:
    """Select only unsubmitted failures from a bounded previous run summary.

    This does not treat a proposed patch as solved. It merely avoids wasting
    model calls on already exported predictions, which should instead be
    independently evaluated. Source issue text and model output are never
    loaded from the previous artifact.
    """
    if not previous.is_file() or previous.stat().st_size > 1_000_000:
        raise ValueError("Previous bounded batch summary is missing or too large")
    try:
        data=json.loads(previous.read_text(encoding="utf-8"))
    except (ValueError,UnicodeError) as exc:
        raise ValueError("Previous batch summary is invalid JSON") from exc
    manifest_ids={task["instance_id"] for task in manifest_tasks}
    if (not isinstance(data,dict) or
            data.get("pinned_manifest_tasks")!=len(manifest_tasks) or
            data.get("officially_evaluated") is not False or
            not isinstance(data.get("tasks"),list)):
        raise ValueError("Retry source must be an unscored batch with original manifest")
    previous_tasks=data["tasks"]
    rows={}
    for record in previous_tasks:
        if (not isinstance(record,dict) or
                not isinstance(record.get("instance_id"),str) or
                not isinstance(record.get("status"),str) or
                record["instance_id"] not in manifest_ids or
                record["instance_id"] in rows):
            raise ValueError("Retry source contains unknown or duplicate instances")
        rows[record["instance_id"]]=record["status"]
    if (not rows or data.get("selected_tasks")!=len(rows) or
            data.get("model_predictions")!=sum(
                status=="model_patch_proposed" for status in rows.values())):
        raise ValueError("Retry source has inconsistent attempt counts")
    missing=data.get("missing_predictions")
    if missing!=len(rows)-data["model_predictions"]:
        raise ValueError("Retry source has inconsistent missing predictions")
    result=[task["instance_id"] for task in manifest_tasks
            if rows.get(task["instance_id"]) in _RETRYABLE_STATUSES]
    if not result:
        raise ValueError("No retryable unsubmitted tasks in previous batch")
    return result


def collect(manifest: Path, output: Path, *, per_task_timeout: int = 240,
            max_steps: int = 10, instance_ids: list[str] | None = None,
            retry_from: Path | None = None) -> dict:
    if not 30 <= per_task_timeout <= 900 or not 2 <= max_steps <= 24:
        raise ValueError("Timeout or agent steps outside safe bounds")
    manifest_tasks = load_manifest(manifest)  # Original 10-20 task safety gate stays intact.
    if retry_from is not None:
        eligible=retryable_task_ids(manifest_tasks,retry_from)
        if instance_ids is None:
            instance_ids=eligible
        elif not isinstance(instance_ids,list) or not set(instance_ids) <= set(eligible):
            raise ValueError("Retry selection must contain only previously unsubmitted failures")
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
                  "failure_category": report.get("failure_category"),
                  "elapsed_ms": round((time.monotonic()-started)*1000),
                  "officially_evaluated": False, "officially_resolved": None}
        record.update(_read_stage(task_output,instance_id))
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
    # Failure taxonomy uses the actual per-task attempt records and never
    # invents official score outcomes. It is safe to publish even if no patch
    # was generated; issue text and model response content are omitted.
    status_counts = {}
    for record in records:
        key=record["status"]
        status_counts[key]=status_counts.get(key,0)+1
    status_counts=dict(sorted(status_counts.items()))
    timeout_stage_counts={}
    for record in records:
        if record["status"]=="model_timeout":
            stage=record.get("last_completed_stage","unknown")
            timeout_stage_counts[stage]=timeout_stage_counts.get(stage,0)+1
    timeout_stage_counts=dict(sorted(timeout_stage_counts.items()))
    summary = {"dataset": "princeton-nlp/SWE-bench_Lite",
               "pinned_manifest_tasks": len(manifest_tasks),
               "selected_tasks": len(tasks),
               "retry_only_unsubmitted_failures": retry_from is not None,
               "model_predictions": len(predictions),
               "missing_predictions": len(tasks)-len(predictions),
               "attempt_status_counts": status_counts,
               "timeout_without_patch": status_counts.get("model_timeout",0),
               "timeout_last_completed_stage_counts": timeout_stage_counts,
               "provider_unavailable_without_patch": status_counts.get("provider_unavailable",0),
               "failed_model_attempt_without_patch": status_counts.get("failed_model_attempt",0),
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
                        help="Optional pinned task IDs; with --retry-from, all IDs must be previously unsubmitted failures")
    parser.add_argument("--retry-from", type=Path,
                        help="A previous unscored summary.json: retry only missing/failed patches")
    args = parser.parse_args(argv)
    summary = collect(args.manifest, args.output,
                      per_task_timeout=args.per_task_timeout,
                      max_steps=args.max_steps, instance_ids=args.instance_ids,
                      retry_from=args.retry_from)
    print(json.dumps({k: v for k, v in summary.items() if k != "tasks"}, indent=2))


if __name__ == "__main__":
    main()
