# RepoPilot — Evidence-first autonomous coding harness

RepoPilot is an independent Python engineering project exploring issue-to-patch automation. The source is inspectable, with explicit trust boundaries and tests.

## Current implementation status (verify before citing)

| Capability | Current implementation | Publicly demonstrated |
|---|---|---|
| Python AST indexing and issue-aware bounded context | Built | Ranked context and safety unit tests in GitHub Actions; model used a simpler context in the prior verified seeded run |
| Model proposal over OpenAI-compatible API | Built | Real Ollama Qwen2.5-coder:3b produced a fix and regression test for seeded issue #1; [verified CI run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44482479486) |
| Public GitHub issue retrieval and opt-in pinned clone | Built | URL parsing and Git checkout command tests in CI; new combined command needs a live model run |
| Issue → proposal → restricted Docker verification | Built | Real model-generated fix passed baseline/reproduction/patched Docker sequence for one seeded integration-test issue; separate reference-patch verification also passes |
| Static pre-execution review and Docker verification | Built | Static review unit tested; still requires human judgment on real patches |\n| Offline dashboard and execution-event report | Built | [Actual Ollama model run](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/model-run.html) and separate [reference patch dashboard](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/review-dashboard.html) |
| Approval-gated draft PR via GitHub API | Built | CLI external API publisher has mock tests; actual [open, unmerged draft PR #2](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/2) was created via connected GitHub for the model-generated seeded fix; CI passed |
| 12 SWE-bench Lite task preparation and result import | Built | Manifest, prediction export and official-result parser added; **0 official issues evaluated** |
| SWE-bench model issue resolution rate | Not measured | **None** |

[Open the recruiter-facing explanation](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/) · [View CI and downloadable run artifacts](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/workflows/repopilot.yml)

## Verified model milestone — November 19, 2026

- [Live Ollama/Qwen 3B verification](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44482479486) fetched [seeded issue #1](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/1), generated a reproduction test and minimal source fix, and proved clean baseline → failing reproduction → passing patched tests in network-restricted Docker.
- [Live model evidence dashboard](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/model-run.html) records the actual run: **35.043 s** end-to-end, **808 provider-reported tokens**. Unambiguous diff formatting was normalized; the model's source-code change was preserved.
- [Draft PR #2](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/2) contains the model-generated fix and regression test. It was opened using connected GitHub access, its CI passed, and it remains **unmerged**.
- This single seeded issue is a controlled integration exercise, **not** an official SWE-bench attempt or generalized agent benchmark.

## Current scope

- Parses local Python repositories with `ast`, without importing target code.
- Calls a configured OpenAI-compatible model API to request a **JSON proposal** containing a reproduction test and unified diff.
- Validates the proposed test path and patch path; no arbitrary shell command is accepted from a model.
- Requires a failing reproduction test **before** applying the patch, then a passing test suite **after** applying it.
- Uses an isolated temporary copy and a restricted Docker container with network disabled.
- Produces a local report. The issue-run command does not publish a PR automatically; the separate draft-PR command requires explicit approval. A real model was called in the linked seeded integration run, but further attempts require provider configuration.\n- Provides optional pinned GitHub checkout and ranked source-context selection, with pre-execution review of proposed patch and regression test. These newer features are CI-tested but have not yet passed a new live-model benchmark.
- A GitHub Actions workflow runs unit tests and proves a real sample reproduction fails before the patch and succeeds afterward inside restricted Docker.

[View RepoPilot CI and Docker verification](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/workflows/repopilot.yml)

## Local usage

Python 3.11+ and Docker are required for the full workflow.

```sh
cd repopilot
python -m pip install -e .
python -m unittest discover -s tests -v
python -m repopilot.cli index examples/calculator
export REPOPILOT_BASE_URL=http://127.0.0.1:11434/v1
export REPOPILOT_MODEL=your-local-model
python -m repopilot.cli propose examples/calculator examples/issue.txt --output .runs/proposal.json
# Review generated proposal and patch first.
docker pull python:3.12-alpine
python -m repopilot.cli verify examples/calculator examples/issue.json --output .runs/verification.json
python -m repopilot.cli dashboard .runs/verification.json --output .runs/dashboard.html
python -m repopilot.cli benchmark .runs/verification.json --dataset "reference-patch fixture"

# When Ollama is running locally and the desired model is already downloaded:
# ollama list
# export REPOPILOT_BASE_URL=http://127.0.0.1:11434/v1
# export REPOPILOT_MODEL=<installed-model-name>
# Run against a public issue URL that applies to the exact local repository version:
# python -m repopilot.cli run /path/to/local/repository https://github.com/OWNER/REPO/issues/NUMBER --output .runs/issue-001


# Optional: let RepoPilot clone the exact upstream revision itself.
# This retrieves public source; it never merges a PR automatically.
# python -m repopilot.cli run-pinned https://github.com/OWNER/REPO/issues/NUMBER \\
#   FULL_40_CHARACTER_PINNED_COMMIT_SHA --output .runs/pinned-issue-001

# Optional: draft PR only AFTER personally inspecting proposal, Docker evidence,
# changed files and confirming the issue matches the target repo.
# export GITHUB_TOKEN=<fine-grained-token-with-contents-and-PR-write-permissions>
# python -m repopilot.cli draft-pr /path/to/local/repository .runs/issue-001/proposal.json .runs/issue-001/run.json --remote OWNER/REPO --approve I_APPROVE_DRAFT_PR

# Select reproducibly: 12 public SWE-bench Lite tasks. This does NOT run them.
# python -m pip install datasets
# python -m repopilot.cli select-swebench --limit 12 --seed 73 --output .runs/swebench-manifest.json
```

For remote providers, set `REPOPILOT_BASE_URL`, `REPOPILOT_MODEL`, and `REPOPILOT_API_KEY` via environment variables. Never commit keys. **Only connect to trusted model endpoints**.

## Threat model and limits

Repository data and issue text are untrusted. Generated patches are never automatically approved. Docker provides defense in depth, not hardened hostile-code isolation. Run verification only on disposable worker machines, without host credentials or Docker socket mounts. Network is disabled within the container; image is pre-pulled. Container timeouts may require manual worker disposal if daemon cleanup fails.

Opt-in pinned public GitHub repository checkout is implemented. There is **no arbitrary-revision automatic cloning** and no unattended merging. GitHub issues can be read via the public REST API. The draft PR CLI publisher's external API route remains mocked in tests. Separately, the authenticated GitHub connector created [real draft PR #2](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/2), CI passed, and it remains unmerged. Neither a SWE-bench resolution score nor model-derived cost or token savings are claimed.

## Benchmark policy

The official [SWE-bench Lite](https://github.com/SWE-bench/SWE-bench) dataset has 300 issue/patch pairs. Its official evaluation harness requires task-specific environments and regression tests; passing RepoPilot's tiny calculator fixture does not mean a SWE-bench instance is resolved.

Select 12 tasks with `select-swebench`, run actual model-generated patches against their pinned base revisions, evaluate with [official SWE-bench tooling](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/evaluation.md), and publish every attempted task, including failures. The reporting module distinguishes reference fixtures and model-generated attempts. The [prediction export](src/repopilot/swebench_export.py) and [official-results import](src/repopilot/swebench_results.py) fail on missing or inconsistent evidence. The [evaluation protocol](benchmarks/README.md) lists task-specific setup requirements. **No benchmark score is available yet.**

## Human reviewer checklist

Before publishing a draft PR, verify the GitHub issue, compare the exact local source with its remote revision, inspect the proposed diff for unrelated changes or secrets, review the test's intent, and confirm the restricted container and CI output. The explicit `I_APPROVE_DRAFT_PR` parameter is a final safeguard, not a substitute for review.

## Recruiter demo

For an accurate 90-second recording and LinkedIn Featured description, see [the recruiter demonstration kit](RECRUITER_DEMO.md).

GitHub Actions produces an artifact named `repopilot-verification-fixture` containing an offline HTML dashboard, verification JSON and an explicitly labeled reference-fixture benchmark report. A real model response or PR appears only after an independently verifiable run.

This project is deliberately distinct from the existing portfolio's browser simulations. Real provider inference and Docker verification have now been demonstrated for **one seeded integration issue only**. Independent SWE-bench issue resolution and success rates are not measured.
