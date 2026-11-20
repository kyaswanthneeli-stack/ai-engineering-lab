"""Replay four preserved v9 proposals for diagnosis only; no model or scoring."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from repopilot.candidate_quality import review_quote_only_patch
from repopilot.candidate_smoke import smoke_candidate
from repopilot.checkout import pinned_checkout
from repopilot.swebench_export import load_manifest
from repopilot.swebench_results import official_summary

SELECTED = ("sympy__sympy-13773", "django__django-12125",
            "matplotlib__matplotlib-22835", "django__django-12589")
SOURCE = "5ffdcd5695fc2df32fef40d0e388a04798f4dee7"


def verified_inputs(manifest, evidence):
    provenance = json.loads((evidence / "provenance.json").read_text())
    if (provenance.get("commit_sha") != SOURCE
            or provenance.get("harness_run_id") != "repopilot-12-qwen3b-v9"
            or provenance.get("github_run_url") !=
            "https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44776554310"):
        raise ValueError("Wrong v9 provenance")
    files = {"manifest": manifest,
             "model_predictions": evidence / "real-model-predictions.jsonl",
             "official_results": evidence / "official-evaluation-result.json",
             "validated_summary": evidence / "official-summary.json"}
    for key, path in files.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != provenance["sha256"][key]:
            raise ValueError("v9 evidence hash mismatch")
    score = official_summary(manifest, files["official_results"], files["model_predictions"])
    if tuple(score[k] for k in ("selected", "submitted", "evaluated", "resolved")) != (12, 6, 6, 1):
        raise ValueError("Unexpected historical v9 counts")
    saved = json.loads(files["validated_summary"].read_text())
    for key, value in score.items():
        if key != "results_path" and saved.get(key) != value:
            raise ValueError("Historical scorecard does not match official output")
    tasks = {row["instance_id"]: row for row in load_manifest(manifest)}
    predictions = {row["instance_id"]: row for row in (
        json.loads(line) for line in files["model_predictions"].read_text().splitlines())}
    if not set(SELECTED) <= predictions.keys() or not set(SELECTED) <= tasks.keys():
        raise ValueError("Missing fixed replay case")
    return tasks, predictions


def replay(manifest, evidence, output, *, label, dataset_loader=None,
           checkout=pinned_checkout, checker=smoke_candidate):
    if output.exists():
        raise ValueError("Refusing to overwrite diagnostic evidence")
    tasks, predictions = verified_inputs(manifest, evidence)
    if dataset_loader is None:
        from datasets import load_dataset
        dataset_loader = lambda: load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    # Read only public issue text/identity. Gold patches and hidden tests are
    # never passed to the model (there is no model), checker or output artifact.
    issues = {}
    for row in dataset_loader():
        instance = row["instance_id"]
        if instance not in SELECTED:
            continue
        task = tasks[instance]
        if row["base_commit"] != task["base_commit"] or row["repo"] != task["repo"]:
            raise ValueError("Public issue identity mismatch")
        issues[instance] = row["problem_statement"]
    if set(issues) != set(SELECTED):
        raise ValueError("Missing public issue")
    output.mkdir(parents=True)
    records = []
    for instance in SELECTED:
        task = tasks[instance]
        prediction = predictions[instance]
        with tempfile.TemporaryDirectory(prefix="repopilot-v9-replay-") as tmp:
            source = checkout(f"https://github.com/{task['repo']}/issues/1",
                              task["base_commit"], Path(tmp) / "repo")
            record = {"instance_id": instance, "base_commit": task["base_commit"],
                      "public_issue_sha256": hashlib.sha256(issues[instance].encode()).hexdigest(),
                      "original_prediction_sha256": hashlib.sha256(
                          prediction["model_patch"].encode()).hexdigest(),
                      "candidate_quality": review_quote_only_patch(source, prediction["model_patch"]),
                      "candidate_smoke": checker(source, prediction["model_patch"],
                                                 issues[instance], timeout=30)}
        records.append(record)
        (output / "progress.json").write_text(json.dumps(records, indent=2) + "\n")
        print(json.dumps(record), flush=True)
    summary = {"kind": "preserved_v9_smoke_replay_not_official_evaluation",
               "label": label, "code_commit": os.getenv("GITHUB_SHA", "local"),
               "historical_prediction_source_commit": SOURCE,
               "selected_tasks": list(SELECTED), "records": records,
               "model_calls": 0, "officially_evaluated": False,
               "officially_resolved": None,
               "confirmed_regressions": sum(row["candidate_smoke"]["status"] == "regression" for row in records),
               "behavior_probe_cases": sum(row["candidate_smoke"].get("probe", "").startswith("source_doctest")
                   and row["candidate_smoke"]["status"] in {"regression", "no_regression_observed"} for row in records),
               "usable_smoke_baselines": sum(row["candidate_smoke"]["status"]
                   in {"regression", "no_regression_observed"} for row in records)}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("benchmarks/swebench-lite-12.json"))
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    replay(args.manifest, args.evidence, args.output, label=args.label)
