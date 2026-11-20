# RepoPilot v8 — independently verified SWE-bench Lite evaluation (November 20, 2026)

**Official outcome: 1/12 selected issues resolved (8.3%). No improvement over v7 (1/12).** The v8 model generated six valid patches, one fewer than v7, and all six submitted predictions were independently evaluated by the official SWE-bench harness. A successful workflow is evidence of completed evaluation, **not** successful bug resolution.

## Exact evidence

- [Official v8 Actions run #44763840558](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44763840558) — both generation and official scoring finished successfully
- [Official scoring artifact #14647687830](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44763840558/artifacts/14647687830) — official `official-evaluation-result.json`, `official-summary.json`, source predictions, SHA-256 provenance
- [Original model attempts artifact #14647591572](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44763840558/artifacts/14647591572) — 12 per-task attempts, authentic patches and candidate-smoke diagnostics
- Source commit `398a010b4a37bb34b147745aaa5d04ad212a6de3`, with opt-in `REPOPILOT_CANDIDATE_SMOKE=1`
- Model `qwen2.5-coder:3b`, native localhost Ollama, pinned `princeton-nlp/SWE-bench_Lite` 12-task cohort, harness run ID `repopilot-12-qwen3b-v8`
- Original submitted prediction JSONL SHA-256: `d78ca82a30158e00857bcf37264bcbd44ea5f920512b319171852620a9bb7ca2`
- Original official-evaluation-result.json SHA-256: `948131c480512b96d92ec9bd6db4694cf2c40aa58a20e1cf39e32e7cf58137d7`
- Original official-summary.json SHA-256: `9133fdd95e27e03e7b75f73660a38fe2b643f5a3b04720085c533f7c14d6183e`
- Original provenance.json SHA-256: `5a2cb51fe2e6142e04cc55d1feed6acd46d1669d65d67c8485130f348e7e4f79`
- Manifest SHA-256 (the same cohort as v7): `1e2f90672055036e11c0bbe4c533e4382fd451a4b021ab7901a3a2881aeed48c`

## Independently verified comparison

| Metric | v7 | v8 |
|---|---:|---:|
| Selected task IDs | 12 | 12 |
| Genuine model-submitted predictions | 7 | 6 |
| Officially evaluated submissions | 7 | 6 |
| Officially resolved | 1 | 1 |
| Officially unresolved submitted | 6 | 5 |
| Evaluator errors | 0 | 0 |
| Not submitted and **not officially evaluated** | 5 | 6 |
| Resolved / selected | 8.3% | 8.3% |
| Resolved / submitted | 14.3% | 16.7% |

The resolution fraction over submitted predictions rose only because **fewer** patches were submitted. There is **no evidence** of greater overall ability to solve the selected issues.

## Exact v8 outcomes

**Officially resolved (1):**
- `sympy__sympy-14774`

**Submitted and officially unresolved (5):**
- `django__django-12125`
- `django__django-12589`
- `matplotlib__matplotlib-22835`
- `scikit-learn__scikit-learn-12471`
- `sympy__sympy-13773`

**Attempted, but no patch submitted and not officially evaluated (6):**
- `django__django-12113` — `TransientOllamaError`
- `django__django-14730` — `TransientOllamaError`
- `sympy__sympy-11870` — `TransientOllamaError`
- `sympy__sympy-20212` — `TransientOllamaError`
- `pytest-dev__pytest-11148` — `AgentToolError`, agent model deadline reached before retry
- `pydata__xarray-4493` — `AgentToolError`, agent model deadline reached before retry

No hard outer 300-second task timeouts were reported.

## Critical new finding: candidate smoke was never decisive

All six genuine submitted predictions contain `candidate_smoke` evidence. Each result was:

```json
{"status":"inconclusive","reason":"baseline_did_not_pass"}
```

Five used a target-module import probe and one used a parseable Python snippet from the public issue. **Zero of six** produced a passing original-code baseline, so **zero** could demonstrate a baseline-pass/candidate-fail regression. In particular, the `sympy__sympy-13773` proposed patch again introduces a suspect `Matrix` type requirement into the point-based geometry constructor, but only an import probe was attempted and the original import did not pass in the minimal container.

The currently used `python:3.12-alpine` offline smoke image does not supply every historical target-repository dependency. The attempt summaries do **not** include diagnostic stack traces by design; therefore a missing or incompatible dependency is the leading practical hypothesis, **not independently proven for each task**. A baseline failure could also result from incomplete runtime setup or a public reproduction failing before the proposed patch.

## Evidence-backed next milestone

1. **Make the baseline useful.** Prepare a **trusted, prebuilt, offline runtime image** with versioned, compatible Python dependencies for smoke runs; never install untrusted repository dependencies or execute arbitrary setup scripts from the repository. Configure the image by a strict developer-owned allowlist, not issue/model-supplied text. Preserve `--network=none`, read-only mounts, nonroot UID, resource limits, timing constraints and fail-closed cleanup. Report baseline failure causes only as bounded safe categories, not raw source or secrets.
2. **Enhance probe relevance.** Mere imports can pass despite a broken constructor; support bounded, predictable original-code behavior/examples when available, without hardcoding gold solutions or running host-side untrusted Python.
3. **Keep an explicit no-false-pass rule.** Missing dependencies, timeout or inconclusive probes never become successful candidate verification; only original-pass and patched-fail is a defensible regression signal.
4. **Retest only after measurable validation improvements.** Compare another independent official benchmark on the same exact 12 tasks and keep selected, submitted, evaluated, resolved, failed and smoke outcomes separate.
5. **Improve Ollama reliability separately** for the four model communication failures and two deadline failures.

The published portfolio prototype and human-reviewed PR safety requirements remain unchanged. This fixed twelve-task research sample is not a result for the entire SWE-bench Lite dataset.