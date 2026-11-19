# RepoPilot v2 development — independently verified SWE-bench Lite comparison

**Verification date:** November 19, 2026  
**Official evaluator source:** [12-task v2 development run #44580636292](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44580636292)  
**Independent audit:** [Run #44594457844](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44594457844)  
**Pinned task cohort:** [swebench-lite-12.json](swebench-lite-12.json)  
**Candidate source commit:** `9c76697068f05535487f9824137c9875b08b1587` (not the final v2 code, and not a v2.0 release).

## Results: no measured improvement yet

| Metric | v1 official baseline | v2 development attempt |
|---|---:|---:|
| Selected pinned issues | 12 | 12 |
| Model-generated patch predictions | 6 | 4 |
| Independently evaluated submissions | 6 | 4 |
| Independently resolved issues | **1** | **1** |
| Officially unresolved submissions | 5 | 3 |
| Not submitted / unscored | 6 | 8 |
| Resolved out of selected cohort | 1/12 (8.3%) | 1/12 (8.3%) |

Only four exact instance IDs received an official evaluation in **both** runs. On those four, the resolved count was **1 versus 1**, a difference of **zero**. The cohort-level number of solved issues also remained unchanged, but coverage of task submissions was *worse* in this v2 development attempt.

## Per-task evidence

| SWE-bench Lite instance | v1 | v2 development | Officially evaluated in both? |
|---|---|---|---|
| `django__django-12113` | Unresolved | No submission | No |
| `django__django-12125` | Unresolved | Unresolved | Yes |
| `django__django-12589` | No submission | No submission | No |
| `django__django-14730` | No submission | No submission | No |
| `matplotlib__matplotlib-22835` | Unresolved | Unresolved | Yes |
| `pydata__xarray-4493` | Unresolved | Unresolved | Yes |
| `pytest-dev__pytest-11148` | No submission | No submission | No |
| `scikit-learn__scikit-learn-12471` | No submission | No submission | No |
| `sympy__sympy-11870` | No submission | No submission | No |
| `sympy__sympy-13773` | Unresolved | No submission | No |
| `sympy__sympy-14774` | **Resolved** | **Resolved** | Yes |
| `sympy__sympy-20212` | No submission | No submission | No |

**Scope:** these are actual model-generated submissions and independent official harness results, not locally seeded patches. The score is NOT a full SWE-bench Lite leaderboard score; it is a 12-issue pinned subset. A timed out or missing prediction is not an officially evaluated failure and is never counted as resolved.

## What this means for v2

This benchmark did not establish any improvement over v1. The v2 branch includes further source-inspection and model-recovery work *after* the evaluated commit, but those later changes have not yet been independently evaluated on the same 12-task cohort.

The immediate focus is reducing the eight no-patch outcomes, improving exact edit generation, and retaining a credible audit trail. Do not release a benchmark-success claim until a fresh official harness run verifies it. No claim of 12/12 or production autonomy.
