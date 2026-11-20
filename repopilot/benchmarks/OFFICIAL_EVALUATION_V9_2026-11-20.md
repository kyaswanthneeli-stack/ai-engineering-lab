# RepoPilot v9 — verified official evaluation, November 20, 2026

**1/12 selected issues resolved (8.3%), unchanged from v8.** Six genuine model
patches were submitted and all six were evaluated: one resolved, five unresolved,
zero evaluator errors. Six attempted tasks produced no submission and received
no official evaluation. A green workflow means evaluation completed.

## Evidence and reproduction

- [Official run #44776554310](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44776554310), source `5ffdcd5695fc2df32fef40d0e388a04798f4dee7`.
- [Official artifact #14655031088](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44776554310/artifacts/14655031088), archive SHA-256 `2c9053d751d0f98af1346e70a62b54f4568c93d4c49602d30c9b6ddb0a46ca10`.
- [Attempt artifact #14652074777](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44776554310/artifacts/14652074777), archive SHA-256 `eb588ec1e46eeef6e5c999eb7f8a5d11fcaf9bd4e3819347bc24ff530c811bbf`.
- Preserved [official output](evidence/v9-2026-11-20/official-evaluation-result.json), [scorecard](evidence/v9-2026-11-20/official-summary.json), [six original predictions](evidence/v9-2026-11-20/real-model-predictions.jsonl), [original provenance](evidence/v9-2026-11-20/provenance.json), [12 attempt records](evidence/v9-2026-11-20/attempt-records.json) and [retrieval checksums](evidence/v9-2026-11-20/retrieval-provenance.json).

Archive hashes were checked against GitHub artifact metadata. Original provenance
hashes were checked against the downloaded official result, predictions, scorecard
and unchanged selection manifest. The twelve attempt objects are aggregated into
one JSON array; the official files are copied byte-for-byte.

From `repopilot/`, reproduce the aggregation without inference or Docker:

```sh
PYTHONPATH=src python -m repopilot.swebench_results \
  benchmarks/swebench-lite-12.json \
  benchmarks/evidence/v9-2026-11-20/official-evaluation-result.json \
  benchmarks/evidence/v9-2026-11-20/real-model-predictions.jsonl
```

The parser validates structure and denominators. The linked run, original
provenance and archive checks supply the separate origin evidence.

## Comparison with v8

| Metric | v8 | v9 |
|---|---:|---:|
| Selected / attempted | 12 | 12 |
| Submitted / officially evaluated | 6 | 6 |
| Resolved | 1 | 1 |
| Unresolved submissions | 5 | 5 |
| Evaluator errors | 0 | 0 |
| No submission, no official evaluation | 6 | 6 |
| Resolved / selected | 8.3% | 8.3% |
| Resolved / evaluated | 16.7% | 16.7% |
| Usable candidate-smoke baselines | 0/6 | 1/6 |
| Confirmed smoke regressions | 0 | 0 |

The v9 prediction file has the same SHA-256 as v8:
`d78ca82a30158e00857bcf37264bcbd44ea5f920512b319171852620a9bb7ca2`.
The official outcome IDs are also identical. The new dependency image made one
weak import baseline usable; this did not improve the submitted patch set or
official resolution count. This small experiment cannot establish general accuracy.

## Every selected task

| Instance | Official outcome | Candidate smoke / generation evidence |
|---|---|---|
| `sympy__sympy-14774` | Resolved | Import baseline did not pass; inconclusive |
| `django__django-12589` | Unresolved | Import baseline and candidate passed; limited probe only |
| `sympy__sympy-13773` | Unresolved | Import baseline did not pass; inconclusive |
| `sympy__sympy-11870` | Not submitted | `TransientOllamaError` |
| `sympy__sympy-20212` | Not submitted | `TransientOllamaError` |
| `django__django-12113` | Not submitted | `TransientOllamaError` |
| `pytest-dev__pytest-11148` | Not submitted | `AgentToolError`: deadline before native retry |
| `django__django-14730` | Not submitted | `TransientOllamaError` |
| `pydata__xarray-4493` | Not submitted | `AgentToolError`: deadline before native retry |
| `scikit-learn__scikit-learn-12471` | Unresolved | Import baseline did not pass; inconclusive |
| `django__django-12125` | Unresolved | Import baseline did not pass; inconclusive |
| `matplotlib__matplotlib-22835` | Unresolved | Issue-example baseline did not pass; inconclusive |

The four Ollama failures are recorded as communication/timeout errors; the
sanitized artifact does not distinguish their underlying network or inference
cause. All six failed attempts finished around the 270-second agent limit.
There were zero hard outer task timeouts. Do not count them as evaluated failures.

Five of six smoke reports remain `inconclusive: baseline_did_not_pass`.
The artifact omits raw baseline stderr, so a per-task dependency, setup or Python
compatibility cause has not been established. The passing Django import probe
did not detect the semantic bug: its patch was officially unresolved.

## Next acceptance gate

The [completed two-task prompt A/B study](CPU_PROMPT_AB_2026-11-20.md) gives mixed
results and does not justify changing the 6,500-character default or launching
another full benchmark. First diagnose baseline failures on pinned checkouts
with bounded, sanitized evidence; verify any runtime/probe correction in real
restricted Docker. Preserve the exact same baseline and candidate probe, and
keep inconclusive outcomes separate from passes. Then use a controlled subset
before another independent official evaluation.
