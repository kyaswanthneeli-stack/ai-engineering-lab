# SWE-bench Lite: 12-task evaluation protocol

**Current verified status:** 12 tasks selected, **0 official task evaluations** and **no SWE-bench resolution rate**.

This folder contains a deterministic sample of twelve real SWE-bench Lite issue IDs and their exact upstream base commits. The manifest does not include a model patch, attempted run, or score.

## Preparing authentic model predictions

For each task, check out its *exact pinned base commit*, fetch its public issue statement, and generate a model patch against that revision. Human-review the patch before writing a task-specific JSON file at `submissions/INSTANCE_ID.json` with the following fields:

```json
{
  "instance_id": "sympy__sympy-14774",
  "base_commit": "8fc63c2d71752389a44367b8ef4aba8a91af6a45",
  "model_name_or_path": "model-name",
  "generated_by_model": true,
  "human_reviewed": true,
  "model_patch": "diff --git a/... b/...\\n--- a/...\\n+++ b/...\\n@@ ... @@\\n"
}
```

Do not include a gold patch, reference solution, or a task that was not actually attempted.

```sh
python -m repopilot.swebench_export \
  benchmarks/swebench-lite-12.json submissions \
  --output .runs/swebench-predictions.jsonl
```

The command fails on malformed / mismatched submissions, exports only model-generated reviewed patches, and prints the number of unattempted tasks. It **never** produces a resolution score.

## Official evaluation

Install and configure the official SWE-bench harness with Docker and enough disk space/compute, then follow [the official evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/). Use a fresh run ID for each patch set, and evaluate against the pinned dataset. For example:

```sh
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Lite \
  --predictions_path .runs/swebench-predictions.jsonl \
  --max_workers 2 \
  --run_id repopilot-lite-12-v1
```

Inspect `logs/evaluation/<run_id>/results.json` and individual `report.json` files. Run the official harness only if predictions exist; there is **no valid benchmark outcome** with an empty prediction file.

## Reporting requirements

Publish all twelve selected IDs. Show predictions submitted, tasks unattempted, official resolved/unresolved/error counts, reproducible run ID, model and cost. Do **not** treat model-suggested patches or RepoPilot's local tests as official SWE-bench resolutions.

**Known limitation:** RepoPilot's current context engine and fixed Python-unittest verifier are built for small Python repositories. Large Django/SymPy/Matplotlib SWE-bench tasks require broader multi-file context, task-specific dependency environments, and full official evaluation. The exporter is infrastructure, not evidence that these tasks have been solved.
