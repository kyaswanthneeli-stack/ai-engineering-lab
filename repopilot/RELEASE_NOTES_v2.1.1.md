# RepoPilot v2.1.1 — Deadline-aware agent reliability patch

**Release date:** November 20, 2026

RepoPilot v2.1.1 packages the already tested [v2.1.0 release](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.1.0), plus [PR #31](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/31) to control model-call time budgets more safely.

## What's fixed

- Each OpenAI-compatible or local native Ollama model request is capped by the remaining agent wall-clock deadline, in addition to the provider's configured per-request timeout.
- Temporary HTTP-error retries and local-only native fallback recompute the remaining time, avoiding late requests that would extend an already-expiring task.
- The agent reserves a small amount of time for patch validation after model inference; independent outer task subprocess timeouts remain in force.
- Added regression tests for deadline caps, local native mode, compatible API requests, late retry prevention and caller-budget propagation.

## Verification and scope

The release workflow verifies Python unit tests, source and official-evidence integrity, restricted Docker fixture regression, build artifacts and clean offline wheel installation. The historical [November 20 SWE-bench Lite result](benchmarks/OFFICIAL_EVALUATION_2026-11-20.md) remains **1/6 submitted, 1/12 selected resolved**, with five unresolved submissions, three model/task timeouts and three model/tool failures. These historical failures motivated the change, but **no new official benchmark has yet established better patch resolution or faster inference**.

## Install, test, and diagnose

```bash
python -m pip install repopilot-2.1.1-py3-none-any.whl
python -m repopilot.cli doctor
```

For source and test reproduction, see [README.md](README.md), [v2.1.0 release notes](RELEASE_NOTES_v2.1.0.md), and the [public walkthrough](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/recruiter-demo.html). Live model repair requires explicit model/provider configuration and a disposable Docker-capable worker; human approval is still required for draft pull requests. This is an evidence-backed engineering prototype, **not** a production-grade general-purpose autonomous coding service.
