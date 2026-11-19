# RepoPilot v2.0 — Development plan

**Status: v2 development, not released.** RepoPilot v1.0.0 is the stable, independently versioned portfolio release. This document tracks proposed improvements without presenting them as delivered production capabilities.

## Target

Make RepoPilot more reliable for real Python projects and larger source trees while retaining the existing security boundaries: no arbitrary model shell commands, safe source paths, restricted test execution, evidence-based benchmark reporting, and human review for merges.

## Milestones and acceptance gates

| Phase | Engineering goal | Evidence required | Status |
|---|---|---|---|
| 1. Deep source inspection | Use issue-named AST symbols and traceback line numbers to inspect the relevant region of long Python files, not the first 120 lines only | Unit tests for named symbols, tracebacks, required targets, unrelated source references, path traversal, and symlinks; full CI and Docker checks | Implemented in v2 development branch; merge pending |
| 2. Large-repository selection | Extend bounded candidate discovery beyond simple alphabetical scanning; consider package paths and import relationships without executing target code | Reproducible tests with large synthetic repository and safe limits; no false assertions about semantic relevance | Planned |
| 3. Agent reliability | Improve prompt/patch retries and preserve validation feedback across truncation; prevent repeated invalid proposals | Model mocked failure tests and one actual model-run artifact | Planned |
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

This is **heuristic, static inspection**. It does not guarantee that the relevant source has been found or that a model patch is correct. The previous v1 official benchmark score remains **one resolved of six evaluated submissions** (one out of 12 selected) until a new independent official run is complete.

## Engineering practice

Keep v1.0.0 at [its immutable release](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v1.0.0). Use a separate v2 feature branch and an open review PR. Every milestone must have tests and evidence before being merged. Do not overwrite or reinterpret the original benchmark artifacts.
