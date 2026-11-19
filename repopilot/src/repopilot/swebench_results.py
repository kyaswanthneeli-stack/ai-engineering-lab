"""Strict aggregation of official SWE-bench evaluator reports.

The aggregator does not execute a benchmark or infer success from a local
RepoPilot test. Missing instances remain unattempted. The input must be a
real official harness result produced from a reviewed prediction batch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from .swebench_export import load_manifest


class EvaluationError(ValueError):
    pass


def official_summary(manifest_path: Path, results_path: Path, predictions_path: Path) -> dict:
    tasks = load_manifest(manifest_path)
    expected = {t["instance_id"] for t in tasks}
    if not results_path.is_file() or not predictions_path.is_file():
        raise EvaluationError("Official results and predictions JSONL must both exist")
    predictions = []
    for line_no, line in enumerate(predictions_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            p = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvaluationError(f"Malformed prediction JSON at line {line_no}") from exc
        if not isinstance(p, dict) or not isinstance(p.get("instance_id"), str):
            raise EvaluationError("Prediction entry lacks instance_id")
        if not isinstance(p.get("model_patch"), str) or not p["model_patch"].strip():
            raise EvaluationError("Empty model patch")
        if not isinstance(p.get("model_name_or_path"), str):
            raise EvaluationError("Missing model identity")
        predictions.append(p["instance_id"])
    submitted = set(predictions)
    if len(submitted) != len(predictions) or not submitted <= expected:
        raise EvaluationError("Duplicate or unexpected predictions")
    try:
        raw = json.loads(results_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvaluationError("Invalid official results JSON") from exc

    # SWE-bench harness results.json uses these outcome arrays.
    if not isinstance(raw, dict) or not {"resolved_ids", "unresolved_ids", "error_ids"} <= set(raw):
        raise EvaluationError("Official results.json requires resolved_ids, unresolved_ids and error_ids")
    results = {}
    for key in ("resolved_ids", "unresolved_ids", "error_ids"):
        value = raw[key]
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise EvaluationError("Invalid official result list: " + key)
        if len(set(value)) != len(value):
            raise EvaluationError("Duplicate official result IDs")
        if not set(value) <= submitted:
            raise EvaluationError("Official results refer to unsubmitted instances")
        results[key] = set(value)
    if results["resolved_ids"] & results["unresolved_ids"] or results["resolved_ids"] & results["error_ids"] or results["unresolved_ids"] & results["error_ids"]:
        raise EvaluationError("Conflicting outcome categories")
    attempted = results["resolved_ids"] | results["unresolved_ids"] | results["error_ids"]
    pending = submitted - attempted
    # Do not treat a partial run as a fully evaluated benchmark.
    resolved = len(results["resolved_ids"])
    outcome_counts = {
        "resolved": resolved,
        "unresolved": len(results["unresolved_ids"]),
        "error": len(results["error_ids"]),
        "submitted_but_unreported": len(pending),
        "not_submitted": len(expected - submitted),
    }
    return {
        "source": "official_swebench_results_json",
        "results_path": str(results_path),
        "selected": len(expected),
        "submitted": len(submitted),
        "evaluated": len(attempted),
        **outcome_counts,
        "resolved_over_evaluated": round(resolved / len(attempted), 4) if attempted else None,
        "resolved_over_selected": round(resolved / len(expected), 4),
        "is_complete_12_task_evaluation": len(submitted) == len(expected) == len(attempted),
        "notes": "Error cases count as not resolved. No result is claimed for missing evaluations. This parser validates structure, not the provenance of supplied files.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("official_results", type=Path)
    parser.add_argument("predictions_jsonl", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    summary = official_summary(args.manifest, args.official_results, args.predictions_jsonl)
    content = json.dumps(summary, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    print(content, end="")


if __name__ == "__main__":
    main()
