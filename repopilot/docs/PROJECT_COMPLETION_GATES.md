# RepoPilot completion gates and next evaluation

**Updated:** November 21, 2026. This document distinguishes a **portfolio-ready, human-supervised Python repair prototype** from an unrestricted production autonomous coding agent.

## Working and evidenced now

- **Portfolio release:** [v2.1.1 stable](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.1.1) and [v2.2.0rc1 prerelease](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.2.0rc1), including the constrained read-only CLI image, operator documentation, security boundaries and rollback guidance.
- **Live issue-to-patch:** A pinned public issue was fetched and a model-generated patch verified against the seeded fixture in restricted Docker. Draft pull requests remain human-approved.
- **CI:** RepoPilot checks and packaging workflow passed for commit `7b8926b9`, including **338 Python unit tests**; verify newer commits separately.
- **Independent benchmark:** Last *fixed full 12-task cohort* official v10 result is **1/12 selected resolved (8.3%)**; four genuine model submissions independently evaluated. See [benchmark evidence](../benchmarks/README.md). This number must not be raised by local probes, submitted patch count, human-written reference fixes or a successful Actions workflow.

## Open gates before closing the active Django investigation

1. Run the pinned `django__django-12113` case with a **model-generated** patch. Keep the initial source, model and any human-supplied issue hints traceable.
2. Pass **all six** trusted SQLite behavior probes: explicit names, distinct persistent files, shared visibility, distinct identity, shared-file setup-once, and in-memory alias identity.
3. Submit only an eligible genuine patch to the independent SWE-bench harness. Require a **resolved** evaluator record, no evaluator error and immutable prediction provenance.
4. Document any model swap or human guidance as a **separate assisted single-case experiment**. This is not a fully autonomous 12-task score.
5. Rerun the identical fixed **12-task** cohort without per-case hand-fed source locations or solution hints before claiming a comparable `2/12` autonomous improvement.
6. Verify the final PR head's repository tests, packaging, security and Docker gates before merging. Keep draft PR approval human-controlled.

## Current next experiment: dedicated coding model

Replace the repeated small-general-model retry with a *single controlled* local Ollama `qwen2.5-coder:7b` assisted attempt. Keep the six pinned probes, known failed-patch fingerprints, independent evaluator and output schema unchanged. Increase bounded request and agent timeouts to account for CPU inference.

**Decision rule:** If the 7B model fails the local probes, preserve the run evidence and stop treating the same issue as ready for final release. Diagnose candidate generation or choose another benchmark task with reliable behavior tests. Do not run a full 12-task benchmark solely to inflate a percentage.

## Definition of done by scope

| Target scope | Readiness | Unfinished evidence |
|---|---|---|
| **Portfolio / demo prototype** | Already demonstrable as prerelease; stable v2.1.1 is published | Final PR review and promotion if the experimental changes are to ship |
| **Higher independently verified bug-solving accuracy** | **Incomplete** | New genuinely resolved official issue; then comparable full-cohort rerun for any improved autonomous score |
| **Unattended production service** | **Not delivered** | Authenticated API/tenant isolation, durable queues, secrets and worker isolation, abuse/rate controls, observability, availability, recovery and deployment verification |

The open Django research PR is not a blocker to *showing the already published portfolio prototype*, but it remains a blocker to claiming the tested six-probe repair improvement or `2/12` independent resolution.
