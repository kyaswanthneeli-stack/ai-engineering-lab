# RepoPilot — recruiter demonstration kit

**Public interactive walkthrough:** https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/recruiter-demo.html

Evidence status: November 19, 2026. This page documents actual completed runs, not simulated successful coding. Recheck live workflow status before reporting newer numbers.

## What is genuinely verified

- **Real Ollama model:** Qwen2.5-Coder 7B generated coordinated edits to `pricing.py` and `checkout.py` for the controlled public [invoice issue #3](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/3).
- **Actual Docker regression:** baseline exit 0, reproduction-before-fix exit 1, post-patch regression exit 0. The reproduction tests were curated independently; do **not** claim the model created them.
- **CI evidence:** [successful real inference + Docker + candidate branch](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44540507015).
- **Actual issue-to-PR:** [draft PR #10](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/10) was opened against main from the verified generated candidate branch. It is **unmerged**, awaiting code review.
- **Separate earlier seeded issue:** [draft PR #2](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/2) has its own verified Ollama 3B + Docker evidence.
- **Independent benchmark:** a [pinned 12-task SWE-bench Lite batch](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44528360120) attempted every selected issue but yielded **zero valid predictions** (11 failures and one timeout). **Official SWE-bench scoring was skipped**, so there is **no official resolution-rate measurement**.

## Ninety-second interview walkthrough

| Time | Show | Accurate explanation |
|---|---|---|
| 0–12 sec | [Interactive demo](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/recruiter-demo.html) | RepoPilot is an evidence-first issue-to-patch Python coding agent with human review gates. |
| 12–25 sec | [Issue #3](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/3) | This is a deliberately controlled two-module invoicing issue, not a public SWE-bench task. |
| 25–43 sec | Interactive demo **Inspection** and **AI edits** | Qwen 7B proposed edits only for guarded inspected source. The system rejects unsafe targets and validates candidate diffs. |
| 43–61 sec | [Actual GitHub Actions run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44540507015) | Baseline tests passed, the curated bug reproduction failed before repair, and Docker passed after the generated changes. |
| 61–76 sec | [Draft PR #10](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/10) | The verified model-generated candidate was published to a branch and opened for **human review**. It is not merged automatically. |
| 76–90 sec | [Honest benchmark tracker](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/benchmark-status.html) | We attempted twelve pinned SWE-bench Lite tasks; no valid predictions emerged, so official scoring was skipped. I report that limitation instead of inventing an accuracy claim. |

## Suggested LinkedIn Featured item

**Title:** RepoPilot — AI Coding Agent with Real Docker-Verified Two-File Repair

**URL:** https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/recruiter-demo.html

**Description:** Built RepoPilot, a Python issue-to-patch coding agent using Ollama/Qwen, bounded repository inspection, guarded model edits and network-restricted Docker verification. Demonstrated a real Qwen 7B-generated two-file fix with a recorded baseline → failing regression → passing patched suite, and published it as an unmerged draft PR for review. GitHub logs and source are linked. Independent SWE-bench evaluation is still in progress; no official score claimed.

## Recording checklist

Record the actual browser pages and CI artifacts. Do not portray the walkthrough's tab controls as live model calls. Do not show private tokens, repository secrets or employer code. Show the public PR and the relevant CI run IDs. Explain which tests were **curated** versus **model-generated**. A draft PR must be inspected and approved before merging.

## Honest resume bullet

> Built RepoPilot, an AI-assisted Python issue-to-patch workflow integrating Ollama/Qwen, bounded code inspection, safe patch validation, Docker regression verification, and human-reviewed GitHub pull requests; demonstrated a real model-generated two-file fix with auditable CI evidence.

Do not state a SWE-bench solve percentage or generalized autonomous coding reliability until official evaluation produces it.
