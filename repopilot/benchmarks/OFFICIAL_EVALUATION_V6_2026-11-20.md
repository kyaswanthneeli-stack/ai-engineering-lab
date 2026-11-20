# RepoPilot v6 — independently verified SWE-bench Lite evaluation (2026-11-20)

**Official result: 1 resolved / 6 submitted (16.7%); 1 resolved / 12 selected (8.3%).** The official score did **not** improve over v5. A successful GitHub Actions evaluation job validates the score, not that all test cases were repaired.

## Evidence and reproducibility

| Field | Verified value |
|---|---|
| [Official v6 workflow run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44743376013) | Completed successfully: generation and independent SWE-bench scoring |
| Source commit | `359b31ea5f7e678cbe3b94fc519de160e2bf4dbb` |
| Model | `qwen2.5-coder:3b`, native local Ollama, 110-second provider calls |
| Dataset | `princeton-nlp/SWE-bench_Lite`, test split, [same fixed 12 selected instances](swebench-lite-12.json) as v5 |
| Official harness run id | `repopilot-12-qwen3b-v6` |
| [Model attempts artifact](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44743376013/artifacts/14634386213) | 12 attempted, 6 real model-generated prediction patches, 6 non-submissions |
| [Official scoring artifact](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44743376013/artifacts/14634866271) | Independent `results.json`, `official-summary.json`, original prediction JSONL, SHA-256 provenance |
| Actual scored outcome | 6 submitted, 6 evaluated, 1 resolved, 5 unresolved, 0 evaluator errors |
| Unsubmitted outcomes | 6 `AgentToolError`: native local Ollama chat failure/timeout, **not officially scored** |
| Hard 300-second task timeouts | **0** (v5 had 3) |

The official results' `resolved_ids` includes only `sympy__sympy-14774`. The five `unresolved_ids` are `django__django-12113`, `matplotlib__matplotlib-22835`, `pydata__xarray-4493`, `scikit-learn__scikit-learn-12471`, and `sympy__sympy-20212`.

The six tasks without patches were `django__django-12589`, `sympy__sympy-13773`, `sympy__sympy-11870`, `pytest-dev__pytest-11148`, `django__django-14730`, and `django__django-12125`. They **must not** be described as officially evaluated or officially unresolved.

## Baseline comparison

| Experiment | Selected | Submitted | Evaluated | Resolved | Resolved/selected | Hard batch timeouts | No-patch model/agent failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| [v5 official baseline](OFFICIAL_EVALUATION_2026-11-20.md) | 12 | 6 | 6 | 1 | 8.3% | 3 | 3 |
| **v6 official experiment** | **12** | **6** | **6** | **1** | **8.3%** | **0** | **6** |

v6 removed hard outer task timeouts but did **not** increase submitted patches or independently confirmed bug solutions. The failure category shifted from three hard timeouts plus three agent/model failures to six native Ollama failures; this is *not evidence* that model inference itself became faster or more accurate.

## SHA-256 for original downloaded artifact members

These values refer to **the original v6 ZIP member bytes**, not any reserialized copy:

- Manifest `swebench-lite-12.json`: `1e2f90672055036e11c0bbe4c533e4382fd451a4b021ab7901a3a2881aeed48c`
- `real-model-predictions.jsonl`: `6d2cc73c80b07feda9b21b47fa9432442260f02402e415f7528a88d072633a8f`
- `official-evaluation-result.json`: `8fa72a5b996fd89a6c43924c9aa9af6a9ac0f30d898f0dd6a700173e2f02ee68`
- `official-summary.json`: `9133fdd95e27e03e7b75f73660a38fe2b643f5a3b04720085c533f7c14d6183e`

Preserved model-patch text SHA-256 by instance: `sympy__sympy-14774` `1211de2e15497ac6e87d2e895d4978d6fe7722637c16dd13b33077e3a46eb0fc`; `sympy__sympy-20212` `b2f87436aad86c1a7b24b8fd809a982d5f68d7b57df53b8f55f3bb5fa505b6af`; `django__django-12113` `ea1643e025ac3004910b40b452131c042c339b7ffc93894417ad406886fac9af`; `pydata__xarray-4493` `db047c3fcd194fbfabc0d0d848980e5f748c9846678623792f2e1707004d71d2`; `scikit-learn__scikit-learn-12471` `976953597bedf3bdf795fc3aa0c16e799a1afdac688b8274a28ee6876c9a9e2a`; `matplotlib__matplotlib-22835` `7a990df62b24ae778bd6281a7390985001e5ecf9e66b8a7999bfa38391ae661f`.

## Evidence-led next engineering actions

1. [PR #37](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/37) introduced bounded transient local Ollama retries and five regression tests; this **postdates v6 generation** and therefore is *not* included in v6's score.
2. Investigate source-file localization and test-only patch proposals. v6 predictions include modifications to `tests/runtests.py` and `xarray/tests/test_variable.py`; both were officially unresolved. Use issue-aware source selection and independent regression tests instead of treating a syntactically valid patch as a resolved issue.
3. Only run another independent real-model benchmark after a measurable improvement is implemented; keep the same 12 task IDs to compare fairly. Never report a higher official solve rate without the actual harness result.

**Limitations:** This deliberately selected 12-task sample is not a result for all 300 SWE-bench Lite tasks, nor production-grade autonomous coding reliability. Human review is required before real project merges. GitHub Actions artifacts expire according to retention settings; their hashes and provenance above allow verification while available.
