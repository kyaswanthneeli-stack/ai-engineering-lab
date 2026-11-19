# RepoPilot v2.0 — Development plan

**Status: v2 development, not released.** RepoPilot v1.0.0 is the stable, independently versioned portfolio release. This document tracks proposed improvements without presenting them as delivered production capabilities.

## Target

Make RepoPilot more reliable for real Python projects and larger source trees while retaining the existing security boundaries: no arbitrary model shell commands, safe source paths, restricted test execution, evidence-based benchmark reporting, and human review for merges.

## Milestones and acceptance gates

| Phase | Engineering goal | Evidence required | Status |
|---|---|---|---|
| 1. Deep source inspection | Use issue-named AST symbols and traceback line numbers to inspect the relevant region of long Python files, not the first 120 lines only | Unit tests for named symbols, tracebacks, required targets, unrelated source references, path traversal, and symlinks; full CI and Docker checks | Implemented in v2 development branch; merge pending |
| 2. Large-repository selection | Filename-token candidate selection beyond the initial AST parse cap; safely prune generated and symlink directories | CI tests for nested sources after 100+ earlier files and strict 20,000-file metadata cap | Filename discovery implemented and CI passed; import-relationship context pending |
| 3. Agent reliability | Reject repeat invalid patch proposals without redundant validation while permitting resubmission after legitimate new source inspection | CI tests for invalid-repeat rejection and proposals becoming valid after inspection, plus one live local-model smoke test | Duplicate-invalid suppression and real-model calculator smoke passed; impact on real SWE-bench success unmeasured |
| 4. Verification and review | Generate additional reproduction tests with clear provenance and evaluate candidate patches in restricted disposable environments | Baseline/reproduction/patched evidence, source-only patch allowlist, reviewer approval | Planned |
| 5. Official benchmark comparison | Run the same pinned SWE-bench cohort and compare genuine official outcomes on overlapping evaluated instances | Two-task pilot and full 12-task runs with actual model patches; real evaluator reports; strict per-instance comparison before claiming improved resolution | Comparator and safe subset runner implemented/tested. Both real benchmark runs in progress; official v2 result pending |
| 6. v2.0 release | Produce a new versioned package, public demo, release notes, security/limitations statement | Green CI, Docker checks, actual benchmark result, wheel and source distribution | Planned |

## First implementation: issue-centered bounded source windows

The first v2 branch adds `issue_window_start(repo, relative_path, issue, count=120)` to the existing context selector and uses it during agent preinspection. The function selects a source excerpt from a safe file by:

1. Trusting only a validated repository-relative `.py` path, never a path suggested by untrusted issue text.
2. Preferring a traceback line **only when it identifies the already selected file**.
3. Otherwise parsing source with Python AST and preferring a named function, async function, or class mentioned in the issue.
4. Falling back to line one when no reliable target is found.
5. Limiting each read to at most 120 lines, preserving the inspected path allowlist, and recording the selected line number in the audit trace.

This is **heuristic, static inspection**. It does not guarantee that the relevant source has been found or that a model patch is correct.

## Second and third improvements: filename discovery and bounded retry hygiene

The filename-only discovery pass scans a capped number of regular Python paths using top-down directory walking. It selects up to 32 paths with matching tokens from the issue, including files beyond the initial AST-parsing cap, without opening every source file. Generated directories and symlink directories are pruned, and the existing independent source-validation rules remain in force. No claim is made that all large repositories or languages are supported.

The model-agent retry loop now hashes a candidate's canonical JSON internally **only after patch validation definitively fails**. An identical rejected edit is not revalidated in a subsequent model step. Proposals that require safe source inspection remain eligible to be resubmitted, so this optimization does not block the existing uninspected-target recovery path. No model output or source is printed in the duplicate-rejection audit message.

[GitHub Actions verification](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44571384204) passed **180 unit tests**, **81% measured code coverage**, and restricted Docker checks. A new real-model/SWE-bench evaluation is still required before asserting any improved AI success rate. The previous v1 official benchmark score remains **one resolved of six evaluated submissions** (one out of 12 selected) until a new independent official run is complete.

## Real-model validation (November 19, 2026)

The [v2 Qwen2.5-Coder 1.5B smoke workflow](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44572068161) **completed successfully**. The agent inspected `calculator.py`, produced its own patch in one model action, and independently verified the patch with restricted Docker baseline/failing-reproduction/patched tests. The GitHub Actions report recorded `model_generated=true`, `verified_in_docker=true`, and `outcome=model_patch_verified`.

This is a **synthetic calculator integration test**, not official SWE-bench evaluation. It does not establish success on large real-world repositories; an independent v2 benchmark comparison remains outstanding.

## Official benchmark development experiments

- [Two-task pilot](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44573511295) uses the unchanged original 12-task manifest and the `--instance-ids` subset option; missing patch predictions must remain **unscored**, and official harness execution is conditional on real predictions.
- [Full 12-task run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44573386221) also started from a batch-runner source update. Neither run's final official outcome was known when this development note was written.
- `repopilot.benchmark_compare` validates both original official score files and submitted prediction JSONL, then only calculates deltas for instance IDs evaluated by the independent harness in **both** runs. It never treats local Docker verification or an unsubmitted patch as resolved.

## Failed Pytest case — provider-timeout recovery

The [first two-task pilot](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44573511295) showed **one official SymPy resolution** and **no Pytest submission**. The archived `pytest-dev__pytest-11148` attempt reported `AgentToolError: Local Ollama native chat failed or timed out`, elapsed approximately 315 seconds. This was a **model-service timeout**, not an officially scored incorrect Pytest patch.

The v2 agent now retries only transient native Ollama HTTP 408/429/5xx, timeout and connection failures up to a configurable bounded count; it classifies wrapped socket timeouts explicitly and does not transmit issue/source content to another host. Unit tests cover recovery, persistent timeouts, HTTP 400 rejection, and no secret leakage.

A [Pytest-only pinned-task retry](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44578518713) uses a locally prewarmed Qwen2.5-Coder 3B model, bounded 180-second native-request timeouts, at most two attempts per model call, and a 900-second task cap. The workflow preserves full evidence and conditionally executes the independent official evaluator only if the model produces a valid prediction. **Its outcome must be read from the completed run and cannot be assumed successful.**

## Pytest follow-up — invalid model edits, not a passing benchmark

The [prewarmed Pytest-only retry](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44578518713) finished with **zero model predictions and no official Pytest evaluation**. The archived attempt showed `failed_model_attempt`: five rejected edits (two invalid Python syntax, one invalid edit schema, one replacement outside inspected source, and one empty/oversized/unchanged edit). GitHub workflow completion must not be mistaken for issue resolution.

The agent's validation-recovery prompt previously requested whole-file `files` replacements even for long Python modules. The v2 fix now recommends short `edits` with verbatim old spans for large inspected source; complete-file corrections remain available only for small modules. This is **model prompting and validation**, not a fabricated reference patch. Regression tests verify the large-file decision and a successful mock recovery.

The [targeted Pytest recovery workflow](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44581523248) reruns the actual pinned task and explicitly fails its final gate unless an independently evaluated prediction **resolves** `pytest-dev__pytest-11148`. Evidence is uploaded even when no patch is generated or the official evaluator rejects it. At the time of this note, the result was **not yet known**. No claim of improved official SWE-bench performance is justified until it finishes.

## Verified v1-to-v2 benchmark audit and ongoing native test

An independently reproduced [12-task official score audit](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44594457844) confirms the previous v2 development run generated **4 valid model predictions**, of which **1 resolved and 3 remained unresolved** in the official harness. Eight other selected tasks produced no valid predictions; none of those eight is counted as an officially evaluated resolution. The comparable four evaluated issues across v1 and v2 showed **zero resolved-count change**. See [full per-issue evidence](benchmarks/V2_OFFICIAL_COMPARISON_2026-11-19.md).

Follow-up improvements include AST/traceback-centered reads for **issue-mentioned source paths**, local Ollama model reuse to reduce cold-start churn, and manual-only expensive full-benchmark scheduling. Current development CI completed [196 Python tests plus restricted Docker verification](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44595002312), with **81% measured code coverage**.

A separate [12-task Qwen3B native-Ollama official run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44595055900) was started from the updated code. Its outcome must not be assumed before the independent official evaluator finishes. A separate [Pytest-only attempt](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44593908576) tests the changed deep-source inspection and recovery prompting. Neither is evidence of additional solved cases until actual scoring confirms it.

## Engineering practice

Keep v1.0.0 at [its immutable release](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v1.0.0). Use a separate v2 feature branch and an open review PR. Every milestone must have tests and evidence before being merged. Do not overwrite or reinterpret the original benchmark artifacts.
