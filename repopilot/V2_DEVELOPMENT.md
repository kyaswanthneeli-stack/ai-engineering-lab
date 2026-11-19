# RepoPilot v2.0 — Development plan

**Status: v2 development, not released.** RepoPilot v1.0.0 is the stable, independently versioned portfolio release. This document tracks proposed improvements without presenting them as delivered production capabilities.

## Target

Make RepoPilot more reliable for real Python projects and larger source trees while retaining the existing security boundaries: no arbitrary model shell commands, safe source paths, restricted test execution, evidence-based benchmark reporting, and human review for merges.

## Milestones and acceptance gates

| Phase | Engineering goal | Evidence required | Status |
|---|---|---|---|
| 1. Deep source inspection | Use issue-named AST symbols and traceback line numbers to inspect the relevant region of long Python files, not the first 120 lines only | Unit tests for named symbols, tracebacks, required targets, unrelated source references, path traversal, and symlinks; full CI and Docker checks | Implemented in v2 development branch; merge pending |
| 2. Large-repository selection | Filename-token candidate selection beyond the initial AST parse cap; safely prune generated and symlink directories | CI tests for nested sources after 100+ earlier files and strict 20,000-file metadata cap | Filename discovery implemented and CI passed; import-relationship context pending |
| 3. Agent reliability | Reject repeat invalid patch proposals without redundant validation while permitting resubmission after legitimate new source inspection | CI tests for invalid-repeat rejection and proposals becoming valid after inspection; future real-model run | Duplicate-invalid suppression implemented and CI passed; real-model improvement not yet verified |
| 4. Verification and review | Generate additional reproduction tests with clear provenance and evaluate candidate patches in restricted disposable environments | Baseline/reproduction/patched evidence, source-only patch allowlist, reviewer approval | Planned |
| 5. Official benchmark comparison | Rerun pinned real SWE-bench tasks against the exact same cohort and publish per-task results | Real model predictions, official SWE-bench evaluator reports, errors/timeouts, and both evaluated-patch and selected-cohort denominators | Planned |
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

## Engineering practice

Keep v1.0.0 at [its immutable release](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v1.0.0). Use a separate v2 feature branch and an open review PR. Every milestone must have tests and evidence before being merged. Do not overwrite or reinterpret the original benchmark artifacts.
