# CPU issue-context A/B — verified results, November 20, 2026

**No consistent improvement: each setting produced one patch from two attempts.**
Keep the default issue-context cap at 6,500 characters. These four exploratory
attempts were not independently scored; no issue resolution or accuracy gain is
established.

## Preserved evidence

- [Completed run #44786475242](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44786475242), source `42a7302fa71c56406323d7445264149c933b5d06`.
- [Original artifact #14655127992](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44786475242/artifacts/14655127992), verified archive SHA-256 `6c75dad04f74c32d1031d0af54b2c8e5791a43937b282d17529f3ef8759f9e50`.
- [Original comparison JSON](evidence/cpu-prompt-ab-2026-11-20/comparison.json), [retrieval checksums](evidence/cpu-prompt-ab-2026-11-20/retrieval-provenance.json), four original attempt records and two original unreviewed model predictions in that directory.
- The workflow verified the exact [official v9 result](OFFICIAL_EVALUATION_V9_2026-11-20.md) before inference. The model was native localhost Ollama `qwen2.5-coder:3b`; pinned upstream commits, 300-second outer timeout, 12-step limit and offline candidate runtime stayed fixed.

## Actual paired outcomes

Times below are end-to-end subprocess elapsed seconds, not pure model latency.

| Task | Default issue chars | Short issue chars | Default time | Short time | Default patch | Short patch |
|---|---:|---:|---:|---:|---|---|
| `django__django-12113` | 4,774 | 2,500 | 88.111 s | 272.945 s | Yes | No: agent deadline |
| `pytest-dev__pytest-11148` | 3,188 | 2,500 | 270.959 s | 79.405 s | No: Ollama error | Yes |

| Metric | Default cap 6,500 | Short cap 2,500 |
|---|---:|---:|
| Attempts | 2 | 2 |
| Genuine proposals accepted by the experiment's format/provenance gate | 1 | 1 |
| Total elapsed seconds | 359.070 | 352.350 |
| Failed model attempts | 1 | 1 |
| Hard outer timeouts | 0 | 0 |
| Usable smoke baselines | 0 | 0 |
| Officially evaluated | 0 | 0 |

The short condition saved 6.720 seconds in aggregate (1.9%) but exchanged which
task produced a patch. One observation per task/condition, failure-censored
latencies, model variability and run-order effects prevent a causal speed claim.
The order was Django default, pytest short, Django short, pytest default.
Patch existence does not establish correctness or independent test success.

Both generated patches had `inconclusive: baseline_did_not_pass` smoke results.
Successful requests reported 2,702 prompt tokens for Django default and 2,736
for pytest short. Failed attempts do not retain comparable request-token counts
or native retry counts. Do not infer those missing values as zero; only the
final recorded error types are known.

The workflow preserved the beginning and end of each shortened issue. Actual
sizes confirm truncation occurred. These artifacts do not establish that all
important reproduction clues survived, nor do they establish either patch fixes
the reported issue.

## Decision

Retain the existing default and the shorter cap as an explicit operator option.
Do not start another twelve-task run on the strength of this study. The next
useful engineering task is to diagnose the inconclusive baseline setup and
validate a correction with a small reproducible Docker experiment. If prompt
optimization is revisited, collect per-call timeout/token evidence and repeated
paired trials, then evaluate actual proposals independently before claiming
better resolution. The verified official cohort result remains **1/12 (8.3%)**.
