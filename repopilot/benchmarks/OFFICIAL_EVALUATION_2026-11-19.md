# RepoPilot official SWE-bench Lite evaluation — November 19, 2026

**This is an actual evaluator result, not an inferred or model-reported success.**

- **Pinned cohort:** 12 selected SWE-bench Lite tasks, with six model-generated patch submissions and six timed-out attempts without submissions.
- **Model:** Qwen2.5-Coder 3B served locally through Ollama on GitHub Actions.
- **Official harness:** `python -m swebench.harness.run_evaluation`, dataset `princeton-nlp/SWE-bench_Lite`, `split=test`, six exact submitted instance IDs.
- **Result:** 1 resolved / 6 officially evaluated; 5 unresolved; 0 evaluation errors. Across the **twelve selected tasks**, exactly one was resolved, with six tasks not submitted.
- **Resolved instance:** `sympy__sympy-14774`.
- **Unresolved submissions:** `sympy__sympy-13773`, `django__django-12113`, `django__django-12125`, `pydata__xarray-4493`, `matplotlib__matplotlib-22835`.
- **Unsubmitted/timed-out:** `django__django-12589`, `sympy__sympy-11870`, `sympy__sympy-20212`, `pytest-dev__pytest-11148`, `django__django-14730`, `scikit-learn__scikit-learn-12471`.

## Auditable evidence

1. [Original generation + official evaluator workflow](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44547336463) completed the six evaluations; the scorer printed `Instances resolved: 1`, `Instances unresolved: 5`, and `Instances with errors: 0`. The workflow *conclusion* was failure only because `actions/upload-artifact` rejected the colon (`:`) in an output filename containing the model name.
2. [Recovery run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44558575315) re-downloaded the **same six generated predictions** from the original run and executed only the official SWE-bench evaluator, not the model. It completed successfully and uploaded a portable official-evidence artifact.
3. [Raw official result JSON in this repository](./official-score-2026-11-19.json) is copied from the recovered `official-evaluation-result.json`. The artifact also contains the real prediction JSONL and a provenance file.

**Metric interpretation:** The official submitted-patch resolution rate is `1/6 = 16.7%`; the selected-cohort resolution count is `1/12 = 8.3%`. Both denominators are documented. These results do **not** establish wider production reliability, cost savings, or performance on the full SWE-bench benchmark.

The separate controlled [invoice issue #3](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/3) model-generated two-file fix and [draft PR #10](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/10) are **not** included in the official SWE-bench results.
