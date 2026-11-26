# SWE-bench Lite: 12-task evaluation protocol

## Unscored v11 7B throughput investigation (November 21, 2026)

The [unassisted v11 12-case attempt](OFFICIAL_V11_7B_2026-11-21.md) tried all 12 pinned issues using Qwen2.5-Coder 7B. It produced **zero valid predictions** (ten transient Ollama failures and two agent-deadline failures); its official SWE-bench scoring job was skipped. This is **unscored**, not a new 0/12 official result. The previously verified v10 full-cohort result remains **1/12 (8.3%)**. [Original GitHub run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44914670302) · [raw artifact](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44914670302/artifacts/14712604395).


## New assisted Django subset (November 21, 2026)

[Qwen2.5-Coder 7B assisted Django evaluation](DJANGO_ASSISTED_7B_2026-11-21.md) generated a model patch for `django__django-12113`, passed **six/six** trusted SQLite probes, and received an official independent **1/1 resolved** verdict with zero evaluator errors. The full original prediction and official result are preserved with digest-verified provenance. **This does not change the 1/12 fixed-cohort autonomous benchmark below:** the local model was different and this Django retry used operator-supplied diagnostic guidance and exact source constraints.

## Official v10 results · November 20, 2026 UTC

**RepoPilot resolved 1 of 12 selected issues (8.3%).** The model attempted all 12 pinned SWE-bench Lite tasks and submitted four patches. The official harness evaluated all four, resolving one (25% of submissions). Eight attempts produced no submission. The harness recorded zero evaluator errors.

| Selected issue | v10 outcome |
|---|---|
| `django__django-12113` | No submission · Ollama chat failure or timeout |
| `django__django-12125` | Unresolved |
| `django__django-12589` | No submission · Ollama chat failure or timeout |
| `django__django-14730` | No submission · Ollama chat failure or timeout |
| `matplotlib__matplotlib-22835` | Unresolved |
| `pydata__xarray-4493` | No submission · agent deadline expired before retry |
| `pytest-dev__pytest-11148` | No submission · agent deadline expired before retry |
| `scikit-learn__scikit-learn-12471` | Unresolved |
| `sympy__sympy-11870` | No submission · Ollama chat failure or timeout |
| `sympy__sympy-13773` | No submission · Ollama HTTP 500 |
| `sympy__sympy-14774` | Resolved |
| `sympy__sympy-20212` | No submission · Ollama chat failure or timeout |

The eight missing predictions account for two-thirds of the cohort. Five attempts reported an Ollama chat failure or timeout, one reported HTTP 500, and two ran out of agent time before a retry. Patch quality was evaluated on the four submissions.

The selected-task score matched v9, while submissions fell from six to four. Both runs resolved the same SymPy issue.

The generation archive contains 12 attempt records. Its four predictions are byte-identical to those in the scoring archive (SHA-256 `70d7c2166772297cdf7e1143db94705eb8a0bc34b52d3a5e05d42cb54e6b07ed`). The official result file and job logs agree on the totals. Model: `qwen2.5-coder:3b`. [Evaluated commit](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/commit/8388139a219d72801f1c06a76ae9a7cd10e821c7) · [Workflow and logs](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44814488203) · [Generation artifact](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44814488203/artifacts/14671703731) · [Scoring artifact](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44814488203/artifacts/14672406833).

## Previous evaluation

**November 20, 2026:** [Official v9](OFFICIAL_EVALUATION_V9_2026-11-20.md) attempted the same 12 pinned tasks, submitted six genuine patches and independently evaluated all six: **one resolved, five unresolved, zero evaluator errors**. Six attempts produced no submission (four Ollama communication/timeout errors and two agent-deadline errors); no hard outer task timeouts occurred. The score remains **1/12 selected (8.3%)**, unchanged from v8; **1/6 evaluated (16.7%)** uses a different denominator. Only **1/6 smoke baselines** was usable. Original v9 results, predictions and provenance are preserved in [evidence](evidence/v9-2026-11-20/). The completed [two-task prompt A/B](CPU_PROMPT_AB_2026-11-20.md) was mixed and unscored; keep the existing default and do not infer a solve-rate gain. Earlier [Nov 20](OFFICIAL_EVALUATION_2026-11-20.md) and [Nov 19](OFFICIAL_EVALUATION_2026-11-19.md) reports remain historical evidence.

This folder contains a deterministic sample of twelve real SWE-bench Lite issue IDs and their exact upstream base commits. The immutable selection manifest intentionally does not include outcomes; results are stored separately to avoid rewriting task provenance.

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

**Known limitation:** RepoPilot is a Python-focused prototype. Large Django/SymPy/Matplotlib SWE-bench tasks need broader context and dedicated dependencies. The **independent official harness** did evaluate six submitted model patches and resolved one; most selected issues remain unresolved or unsubmitted. The exporter alone does not establish a solve.
## Controlled smoke validation replay

The [four-case historical v9 replay](SMOKE_REPLAY_2026-11-20.md) diagnosed
runtime blockers and measured usable smoke baselines increasing from **1/4 to
3/4** with opt-in import setup. It reuses original patches with no model calls,
and does not change the independently verified **1/12** resolution result.
Matplotlib remains inconclusive because the native extension is unavailable.
