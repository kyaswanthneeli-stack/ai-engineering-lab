# Case study: first official SWE-bench issue resolved by RepoPilot

**Benchmark instance:** `sympy__sympy-14774`  
**Source repository:** `sympy/sympy`  
**Pinned base commit:** `8fc63c2d71752389a44367b8ef4aba8a91af6a45`  
**Model:** local Ollama `qwen2.5-coder:3b`  
**Date of official evaluation:** November 19, 2026  
**Official result:** **RESOLVED** by the SWE-bench Lite harness, with no evaluator error.

## The concrete generated repair

RepoPilot generated a minimal patch in `sympy/printing/latex.py`. The relevant change expands the inverse-trigonometric function list used by the LaTeX printer.

```diff
-            inv_trig_table = ["asin", "acos", "atan", "acot"]
+            inv_trig_table = ["asin", "acos", "atan", "acsc", "asec", "acot"]
```

The patch adds `acsc` and `asec` to that classification. It was not copied from the benchmark's reference patch by the evaluation pipeline. The actual model-generated patch can be inspected in [the published predictions JSONL](official-predictions-2026-11-19.jsonl), where the record has `instance_id=sympy__sympy-14774`. Its SHA-256 is `1211de2e15497ac6e87d2e895d4978d6fe7722637c16dd13b33077e3a46eb0fc`.

## Why the result is credible

1. RepoPilot selected this task from a fixed manifest of 12 SWE-bench Lite instances.
2. The agent used a local LLM to propose a patch against the upstream pinned source.
3. Six model-generated predictions were exported in the benchmark's JSONL format; six other attempts timed out without patches.
4. The independent official SWE-bench harness evaluated all six submitted patches. Its report marked **this exact SymPy instance resolved**, five other instances unresolved and zero instances as evaluation errors.
5. The original run's final artifact upload failed solely because the generated report filename included a colon. A second scoring-only workflow reused **the same prediction file**, reran the official harness, and successfully uploaded the authoritative report.

## Reproduce this evaluation

Use a disposable Docker-capable evaluation worker. The following command uses the **original six model-generated predictions**, not a reference answer:

```bash
cd repopilot
python -m pip install 'swebench>=3.0,<5.0'
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Lite \
  --split test \
  --predictions_path benchmarks/official-predictions-2026-11-19.jsonl \
  --instance_ids sympy__sympy-14774 \
  --max_workers 1 \
  --run_id repopilot-sympy-14774-reproduction
```

The published [official result record](official-score-2026-11-19.json) and the immutable patch-hash regression test at `tests/test_published_official_evidence.py` allow independent consistency checks without rerunning expensive containers.

## Evidence

- [Original generation and official evaluation](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44547336463)
- [Successful official evidence recovery](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44558575315)
- [Official result JSON](official-score-2026-11-19.json)
- [Original six model predictions](official-predictions-2026-11-19.jsonl)

**Limits:** This case proves one resolved official task in the pinned 12-task sample; it does not establish the reliability of RepoPilot on the full 300-task SWE-bench Lite set, other programming languages, or production repositories. The separate controlled invoice repair and draft PR #10 are not included in this benchmark.
