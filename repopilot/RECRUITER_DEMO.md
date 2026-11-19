# RepoPilot recruiter demonstration kit

**Use this material with the real, publicly verifiable demonstration.** This is a recording outline and link package, not a prerecorded video. Do not claim results from tasks that were never evaluated.

## Suggested LinkedIn Featured item

- **Title:** RepoPilot — AI Coding Agent with Verified Docker Tests
- **URL:** https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/
- **Description:** Inspect a real Ollama Qwen2.5-Coder 3B run that fetched a seeded GitHub issue, proposed a reproduction test and patch, and passed baseline → fail-before → pass-after Docker verification. Includes source, CI, execution report and an open draft PR for human review. No SWE-bench results are claimed.

## 90-second screen recording outline

| Time | Show on screen | Narration |
|---|---|---|
| 0–12 s | The RepoPilot project landing page | "RepoPilot is my Python issue-to-patch engineering harness. I built it to make agent coding results inspectable rather than merely plausible." |
| 12–25 s | GitHub issue #1 | "Here is a deliberately seeded division-by-zero bug. It provides a small, reproducible integration case." |
| 25–43 s | Real model-run page | "A Qwen 3B model running through Ollama generated a proposed patch and a reproduction test. The run did not assume that the model's output was valid." |
| 43–62 s | GitHub Actions CI job and before/after evidence | "The baseline tests passed, the new reproduction test failed before the patch, and the entire test suite passed after the patch in a network-restricted Docker container." |
| 62–77 s | Open draft PR #2, Files Changed | "The patch and regression test were published as an open draft pull request for human review; nothing was merged automatically." |
| 77–90 s | Public benchmark-status page | "I selected twelve real SWE-bench Lite tasks, but have not run them yet. The project reports that honestly rather than inventing a success rate." |

## Direct evidence links

- [Recruiter project overview](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/)
- [Real model execution evidence](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/model-run.html)
- [Verified GitHub Actions run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44482479486)
- [Seeded public issue #1](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/1)
- [Open draft PR #2](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/2)
- [12-task benchmark progress](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/benchmark-status.html)
- [RepoPilot source](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/tree/main/repopilot)

## Accurate LinkedIn post draft

> I built RepoPilot, a Python issue-to-patch harness for inspecting AI coding proposals against real tests.
>
> In a public integration run, a local Ollama Qwen2.5-Coder 3B model read a deliberately seeded GitHub issue, generated a reproduction test and patch, and passed three Docker verification stages: existing tests green, new test failing before the fix, and all tests passing after.
>
> The proposed change is visible in an open, unmerged draft PR. I've also published a 12-task SWE-bench Lite evaluation manifest—but those benchmark tasks are **not yet attempted**, and I'm not claiming a resolution percentage.
>
> Source, CI logs and run evidence: https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/
>
> #Python #GenerativeAI #AgenticAI #SoftwareEngineering #DevTools

## Recording checklist

Record a real browser walkthrough rather than creating a synthetic animation and calling it a live run. Keep the issue, Actions log, PR and source URLs visible. Do not disclose API keys, local credentials, employer source code or private conversations. State clearly that the demonstrated issue is intentionally simple and seeded.
