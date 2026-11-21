# RepoPilot completion gates and next evaluation

**Updated:** November 21, 2026. This document distinguishes a **portfolio-ready, human-supervised Python repair prototype** from an unrestricted production autonomous coding agent.

## Working and evidenced now

- **Portfolio release:** [v2.1.1 stable](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.1.1) and [v2.2.0rc1 prerelease](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.2.0rc1), including the constrained read-only CLI image, operator documentation, security boundaries and rollback guidance.
- **Live issue-to-patch:** A pinned public issue was fetched and a model-generated patch verified against the seeded fixture in restricted Docker. Draft pull requests remain human-approved.
- **CI:** RepoPilot checks and packaging workflow passed for commit `6aaf3fa1`, including **339 Python unit tests**; verify newer commits separately.
- **Independent benchmark:** An assisted 7B single-case Django patch passed **6/6** local regressions and was **officially resolved 1/1**; see [Django official evidence](../benchmarks/DJANGO_ASSISTED_7B_2026-11-21.md). The last *comparable full 12-task cohort* v10 remains **1/12 (8.3%)**. Different models and human-assisted subsets cannot be combined into a new autonomous cohort score.

## Open gates before closing the active Django investigation

1. Run the pinned `django__django-12113` case with a **model-generated** patch. Keep the initial source, model and any human-supplied issue hints traceable.
2. Pass **all six** trusted SQLite behavior probes: explicit names, distinct persistent files, shared visibility, distinct identity, shared-file setup-once, and in-memory alias identity.
3. Submit only an eligible genuine patch to the independent SWE-bench harness. Require a **resolved** evaluator record, no evaluator error and immutable prediction provenance.
4. Document any model swap or human guidance as a **separate assisted single-case experiment**. This is not a fully autonomous 12-task score.
5. Rerun the identical fixed **12-task** cohort without per-case hand-fed source locations or solution hints before claiming a comparable `2/12` autonomous improvement.
6. Verify the final PR head's repository tests, packaging, security and Docker gates before merging. Keep draft PR approval human-controlled.

## Completed assisted 7B result and the next experiment

The dedicated local Ollama `qwen2.5-coder:7b` model produced a valid two-line Django patch that passed all six pinned SQLite probes and the independent official evaluator: **1/1 resolved** on this assisted subset. Original prediction and evaluator output with SHA-256 checks are preserved in the evidence folder linked above.

**Next decision:** Prepare an unassisted, comparable **fixed 12-task** run using a consistent model configuration and original issue text, without the task-specific hand-fed source diagnosis or solution hints. Inspect the outcome independently and report all attempted, submitted, resolved and missing tasks. An additional 12-task benchmark should be launched only with adequate CPU/runner budget and its own bounded timeout/provenance plan.

## Next independent whole-cohort benchmark: v11

[Unassisted Qwen2.5-Coder 7B workflow](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/blob/bench/repopilot-django-behavior/.github/workflows/repopilot-official-12-v11-7b-evaluation.yml) attempts **all the same 12 pinned SWE-bench Lite issues** with uniform model settings and the general `repopilot.benchmark_batch --agentic` path, not the task-specific Django assisted retry. It preserves original problem statements (with the existing bounded context reduction), the ordinary autonomous source inspection policy, each attempt record, raw model predictions, and evaluator/provenance hashes. Candidate submissions must still pass the independent official SWE-bench harness, which records failures and absent patches.

**Acceptance condition:** Only the v11 official evidence can support a new full-cohort score; 2/12 is a target, not an achieved result. A changed model is an explicit experimental variable relative to the v10 3B baseline. Generation on a CPU runner can take substantial runtime; a workflow that merely completes, reports zero predictions, or skips scoring is not a verified resolution result.

## Definition of done by scope

| Target scope | Readiness | Unfinished evidence |
|---|---|---|
| **Portfolio / demo prototype** | Already demonstrable as prerelease; stable v2.1.1 is published | Final PR review and promotion if the experimental changes are to ship |
| **Higher independently verified bug-solving accuracy** | **Assisted Django subset independently resolved; full-cohort improvement still unproven** | Comparable unassisted fixed-cohort rerun before claiming 2/12 |
| **Unattended production service** | **Not delivered** | Authenticated API/tenant isolation, durable queues, secrets and worker isolation, abuse/rate controls, observability, availability, recovery and deployment verification |

The Django six-probe repair is now demonstrated and independently resolved as an assisted single-case result. The research PR is not a blocker to *showing the already published portfolio prototype*. Review and merge verified changes as appropriate; **do not claim a new 2/12 autonomous result** without the comparable full-cohort run.
