# RepoPilot official SWE-bench Lite result — November 20, 2026

**Verified official harness outcome: 1 resolved of 6 model-generated submissions (16.7%); 1 resolved of 12 pinned selected tasks (8.3%).** This **did not improve** on the independently preserved November 19 baseline. A passing GitHub workflow is not a claim that all issues were solved.

## Provenance and independent verification

| Field | Value |
|---|---|
| Workflow | [Official 12-task evaluation, run #44703057273](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44703057273) |
| Source commit | [`048efaeb0cd7cba2e3a2c1d92e6a4d9ef9c8da2c`](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/commit/048efaeb0cd7cba2e3a2c1d92e6a4d9ef9c8da2c) |
| Manifest | [12 fixed instance IDs and pinned commits](swebench-lite-12.json) |
| Dataset | `princeton-nlp/SWE-bench_Lite`, test split |
| Model | `qwen2.5-coder:3b` served locally through Ollama (native JSON mode) |
| Generation | 12 task attempts; 6 exported model patches; 3 hard 300-second task timeouts; 3 non-timeout agent/model failures |
| Official harness | `python -m swebench.harness.run_evaluation`, only on the six submitted prediction IDs |
| Scoring | 6 submitted, 6 evaluated, 1 resolved, 5 unresolved, 0 evaluator errors |
| Artifact with raw attempts | [`repopilot-12-model-attempts-v5-unscored`, artifact #14615991492](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44703057273) |
| Artifact with official results | [`repopilot-12-official-harness-v5`, artifact #14616122611](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44703057273) |

The official scoring job completed **successfully**. Its console output explicitly reported `Instances submitted: 6`, `Instances resolved: 1`, `Instances unresolved: 5`, and `Instances with errors: 0`. The model-generation job also completed successfully as a **batch orchestration job**, not because every instance generated a correct patch.

## Model-generated candidates and official outcomes

| Instance | Prediction | Official outcome |
|---|---|---|
| `sympy__sympy-14774` | Submitted | **Resolved** |
| `django__django-12113` | Submitted | Unresolved |
| `pydata__xarray-4493` | Submitted | Unresolved |
| `scikit-learn__scikit-learn-12471` | Submitted | Unresolved |
| `django__django-12125` | Submitted | Unresolved |
| `matplotlib__matplotlib-22835` | Submitted | Unresolved |
| `sympy__sympy-11870` | No patch | 300-second task timeout; **not officially evaluated** |
| `pytest-dev__pytest-11148` | No patch | 300-second task timeout; **not officially evaluated** |
| `django__django-14730` | No patch | 300-second task timeout; **not officially evaluated** |
| `django__django-12589` | No patch | `AgentToolError`; **not officially evaluated** |
| `sympy__sympy-13773` | No patch | `AgentToolError`; **not officially evaluated** |
| `sympy__sympy-20212` | No patch | `AgentToolError`; **not officially evaluated** |

These statuses come from the original batch `summary.json` and the independent official evaluator's `results.json`. **Do not label the six unsubmitted tasks "officially unresolved"**; the official harness never evaluated patches for them.

## Permanent evidence preserved in this repository

- [Official evaluator result JSON](official-score-2026-11-20.json): copied from the original official scoring artifact, with equivalent JSON formatting.
- [Six authentic model-generated prediction patches](official-predictions-2026-11-20.jsonl): copied from the original artifact as JSONL (re-serialized whitespace only).
- [Automated patch-hash and score validation](../tests/test_published_official_evidence_nov20.py): verifies that all six patch texts have the original SHA-256 values and that the official selected / submitted / resolved counts reconcile.

**SHA-256 of original artifact file bytes** (GitHub's ZIP contents before JSON whitespace normalization):

- `real-model-predictions.jsonl`: `fb377e5d3761d67820cbe85cd09143722408794b4af12820aed49500c57bcb05`
- `official-evaluation-result.json`: `1800f2fd1777bd99fb3fa52150d6261f5aaff0cc3ac0bed1754e54ab4647db6a`

Preserved patch text checksums are verified by the test suite, rather than pretending these re-serialized copies have the same whole-file hash as the original ZIP members.

## Comparison with prior evidence

| Cohort | Selected | Submitted | Officially resolved | Resolved/submitted | Resolved/selected |
|---|---:|---:|---:|---:|---:|
| [Nov 19 original](OFFICIAL_EVALUATION_2026-11-19.md) | 12 | 6 | 1 | 16.7% | 8.3% |
| [Nov 19 later evaluation](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44580636292) | 12 | 4 | 1 | 25.0% | 8.3% |
| **Nov 20 current** | **12** | **6** | **1** | **16.7%** | **8.3%** |

The one resolved task was `sympy__sympy-14774` in the current result. This sample does **not** establish production reliability, benchmark-wide performance on all 300 SWE-bench Lite tasks, reduced cost, or a guaranteed rate of autonomous repair. A human reviewer remains responsible for any real repository merge.
