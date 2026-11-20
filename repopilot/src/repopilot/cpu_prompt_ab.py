"""Small, unscored CPU Ollama issue-prompt A/B experiment.

Two fixed public SWE-bench Lite task IDs, two context caps, one pinned model.
Uses genuine model proposals but deliberately does NOT run an official evaluator
or claim solved issues. A/B findings are exploratory, not causal guarantees.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from .swebench_export import load_manifest
from .patches import validate_patch

# One task formerly emitted a patch; the other frequently exhausted its CPU
# deadline. Both official problem statements exceed the 2500-character cap.
# Order balances prompt configuration across an identical warmed model/runner.
DJANGO = "django__django-12113"
PYTEST = "pytest-dev__pytest-11148"
ORDER = ((DJANGO, 6500), (PYTEST, 2500),
         (DJANGO, 2500), (PYTEST, 6500))


def _verified_prediction(output: Path, instance: str, commit: str) -> bool:
    """Only call an artifact a genuine valid proposal when provenance matches."""
    try:
        record = json.loads(
            (output / "unreviewed-prediction.json").read_text(encoding="utf-8"))
        if (not isinstance(record, dict)
                or record.get("instance_id") != instance
                or record.get("base_commit") != commit
                or record.get("generated_by_model") is not True
                or record.get("human_reviewed") is not False
                or not isinstance(record.get("model_name_or_path"), str)
                or not record["model_name_or_path"]
                or not isinstance(record.get("model_patch"), str)):
            return False
        validate_patch(record["model_patch"])
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False


def compare_two_pinned_tasks(
    manifest: Path, output: Path, *, per_task_timeout: int = 300,
    max_steps: int = 12, run=subprocess.run,
) -> dict:
    if not 30 <= per_task_timeout <= 900 or not 2 <= max_steps <= 24:
        raise ValueError("Timeout or model steps outside safe bounds")
    tasks = {task["instance_id"]: task for task in load_manifest(manifest)}
    if set((DJANGO, PYTEST)) - set(tasks):
        raise ValueError("A/B tasks must be present in original pinned cohort")
    if output.exists():
        raise ValueError("Refusing to overwrite experimental evidence")
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for index, (instance, cap) in enumerate(ORDER, 1):
        condition = "short" if cap == 2500 else "default"
        task = tasks[instance]
        run_dir = output / f"{index:02d}-{instance}-{condition}"
        env = dict(os.environ)
        env["REPOPILOT_ISSUE_CONTEXT_CHARS"] = str(cap)
        command = [
            sys.executable, "-m", "repopilot.benchmark_attempt",
            instance, "--agentic", "--max-steps", str(max_steps),
            "--manifest", str(manifest), "--output", str(run_dir),
        ]
        started = time.monotonic()
        process_status = "completed"
        try:
            finished = run(
                command, env=env, timeout=per_task_timeout, check=False,
                capture_output=True, text=True,
            )
            exit_code = finished.returncode
        except subprocess.TimeoutExpired:
            exit_code = None
            process_status = "outer_timeout"
        except OSError:
            exit_code = None
            process_status = "launch_failed"
        elapsed_ms = round((time.monotonic() - started) * 1000)
        try:
            evidence = json.loads((run_dir / "attempt.json").read_text(encoding="utf-8"))
            if not isinstance(evidence, dict):
                raise ValueError("Bad attempt record type")
        except (OSError, ValueError, TypeError):
            evidence = {}
        valid = (process_status == "completed"
                 and evidence.get("status") == "model_patch_proposed"
                 and _verified_prediction(run_dir, instance, task["base_commit"]))
        smoke = evidence.get("candidate_smoke")
        row = {
            "instance_id": instance,
            "base_commit": task["base_commit"],
            "cap_chars": cap,
            "condition": condition,
            "run_index": index,
            "process_status": process_status,
            "process_exit_code": exit_code,
            "attempt_status": evidence.get("status", "missing_or_invalid_record"),
            "error_type": evidence.get("error_type"),
            "elapsed_ms": elapsed_ms,
            "model_elapsed_ms": evidence.get("elapsed_ms"),
            "actual_issue_chars": evidence.get("issue_context_chars"),
            "issue_trimmed": evidence.get("issue_context_trimmed"),
            "agent_steps": evidence.get("agent_steps"),
            "model_generated_patch": bool(valid),
            "candidate_smoke_status":
                smoke.get("status") if isinstance(smoke, dict) else None,
            "candidate_smoke_reason":
                smoke.get("reason") if isinstance(smoke, dict) else None,
            "officially_evaluated": False,
            "officially_resolved": None,
        }
        rows.append(row)
        (output / "progress.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(f"[{index}/4] {instance} {condition}: {row['attempt_status']}",
              flush=True)
    pairs = []
    for instance in (DJANGO, PYTEST):
        entries = [x for x in rows if x["instance_id"] == instance]
        a = next(x for x in entries if x["condition"] == "default")
        b = next(x for x in entries if x["condition"] == "short")
        pairs.append({
            "instance_id": instance,
            "original_default_issue_chars": a["actual_issue_chars"],
            "short_issue_chars": b["actual_issue_chars"],
            "default_elapsed_ms": a["elapsed_ms"],
            "short_elapsed_ms": b["elapsed_ms"],
            "default_generated_patch": a["model_generated_patch"],
            "short_generated_patch": b["model_generated_patch"],
            "default_error_type": a["error_type"],
            "short_error_type": b["error_type"],
            "short_issue_truncated": b["issue_trimmed"],
        })
    summary = {
        "kind": "controlled_small_sample_unscored_model_generation",
        "dataset": "princeton-nlp/SWE-bench_Lite",
        "selected_task_ids": [DJANGO, PYTEST],
        "unique_selected_tasks": 2,
        "attempts": 4,
        "conditions": {"default_issue_chars": 6500, "short_issue_chars": 2500},
        "model_generated_patches": sum(row["model_generated_patch"] for row in rows),
        "officially_evaluated": False,
        "officially_resolved": None,
        "notes": (
            "Real model patches, no gold patches, no independent SWE-bench "
            "evaluation. Two tasks with one observation per condition: "
            "feasibility evidence only; do not claim a solve-rate gain."
        ),
        "pairs": pairs,
        "records": rows,
    }
    (output / "comparison.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path,
                        default=Path("benchmarks/swebench-lite-12.json"))
    parser.add_argument("--output", type=Path,
                        default=Path(".runs/cpu-prompt-ab"))
    parser.add_argument("--per-task-timeout", type=int, default=300)
    parser.add_argument("--max-steps", type=int, default=12)
    args = parser.parse_args(argv)
    result = compare_two_pinned_tasks(
        args.manifest, args.output,
        per_task_timeout=args.per_task_timeout, max_steps=args.max_steps)
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("records", "pairs")}, indent=2))


if __name__ == "__main__":
    main()
