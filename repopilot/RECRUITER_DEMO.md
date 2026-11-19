# RepoPilot recruiter demonstration kit

**Use this material with the real, publicly verifiable demonstration.** This is a recording outline and link package, not a prerecorded video. Do not claim results from tasks that were never evaluated.

## Suggested LinkedIn Featured item

- **Title:** RepoPilot — AI Coding Agent with Verified Docker Tests
- **URL:** https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/
- **Description:** See two independently verified synthetic AI coding challenges: a Qwen 3B single-file fix and a Qwen 7B model-generated **two-file** invoice fix. Both passed baseline → fail-before → pass-after Docker tests. The 7B run modified `pricing.py` and `checkout.py` in six agent steps. Twelve real SWE-bench issues were attempted but yielded no valid submitted predictions; no official score is claimed.

## 90-second screen recording outline

| Time | Show on screen | Narration |
|---|---|---|
| 0–12 s | The RepoPilot project landing page | "RepoPilot is my Python issue-to-patch engineering harness. I built it to make agent coding results inspectable rather than merely plausible." |
| 12–25 s | GitHub issue #1 | "Here is a deliberately seeded division-by-zero bug. It provides a small, reproducible integration case." |
| 25–43 s | Real model-run page | "A Qwen 3B model running through Ollama generated a proposed patch and a reproduction test. The run did not assume that the model's output was valid." |
| 43–62 s | GitHub Actions CI job and before/after evidence | "The baseline tests passed, the new reproduction test failed before the patch, and the entire test suite passed after the patch in a network-restricted Docker container." |
| 62–77 s | Open draft PR #2, Files Changed | "The patch and regression test were published as an open draft pull request for human review; nothing was merged automatically." |
| 77–90 s | Verified Qwen 7B multi-file workflow, then benchmark page | "A second model changed two source files and passed Docker regression. All twelve SWE-bench issues were attempted separately, with no valid predictions or official score yet." |

## Direct evidence links

- [Recruiter project overview](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/)
- [Real model execution evidence](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/model-run.html)
- [Verified GitHub Actions run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44482479486)
- [Seeded public issue #1](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/1)
- [Open draft PR #2](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/2)
- [Verified Qwen 7B two-file CI and artifacts](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44538875317)
- [Public invoice challenge #3](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/3)
- [Actual 12-task model-attempt evidence (0 valid patches)](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44528360120)
- [12-task benchmark progress](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/benchmark-status.html)
- [RepoPilot source](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/tree/main/repopilot)

## Accurate LinkedIn post draft

> I built RepoPilot, a Python issue-to-patch harness for inspecting AI coding proposals against real tests.
>
> In a public integration run, a local Ollama Qwen2.5-Coder 3B model read a deliberately seeded GitHub issue, generated a reproduction test and patch, and passed three Docker verification stages: existing tests green, new test failing before the fix, and all tests passing after.
>
> A second real Qwen 7B run generated a patch across two invoice modules and passed the same Docker baseline → fail-before → pass-after sequence in six agent steps. These are **synthetic integration examples**, not SWE-bench solutions. All twelve pinned SWE-bench Lite issues were attempted, but yielded **zero valid exported predictions**, so no official score is claimed.
>
> Source, CI logs and run evidence: https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/
>
> #Python #GenerativeAI #AgenticAI #SoftwareEngineering #DevTools

## Recording checklist

Record a real browser walkthrough rather than creating a synthetic animation and calling it a live run. Keep the issue, Actions log, PR and source URLs visible. Do not disclose API keys, local credentials, employer source code or private conversations. State clearly that the demonstrated issue is intentionally simple and seeded.
