# RepoPilot — Evidence-first autonomous coding harness

RepoPilot is an independent Python engineering project exploring issue-to-patch automation. The source is inspectable, with explicit trust boundaries and tests.

## Current implementation status (verify before citing)

| Capability | Current implementation | Publicly demonstrated |
|---|---|---|
| Python AST indexing and issue-aware bounded context | Built | Ranked context and safety unit tests in GitHub Actions; model used a simpler context in the prior verified seeded run |
| Model proposal over OpenAI-compatible API | Built | Real Ollama Qwen2.5-coder:3b produced a fix and regression test for seeded issue #1; [verified CI run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44482479486) |
| Public GitHub issue retrieval and opt-in pinned clone | Built | [Actual end-to-end live model + pinned clone + Docker CI](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44497087568) passed |
| Issue → proposal → restricted Docker verification | Built | Seeded #1 verified. Qwen 7B two-file #3 passed initial Docker regression, but human review found incomplete direct `taxable_subtotal` validation; stronger tests underway. |
| Static pre-execution review and Docker verification | Built | Static review unit tested; still requires human judgment on real patches |
| Offline dashboard and execution-event report | Built | [Actual Ollama model run](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/model-run.html) and separate [reference patch dashboard](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/review-dashboard.html) |
| Approval-gated draft PR via GitHub API | Built | CLI external API publisher has mock tests; actual [open, unmerged draft PR #2](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/2) was created via connected GitHub for the model-generated seeded fix; CI passed |
| 12 SWE-bench Lite task preparation and result import | Built | All 12 pinned tasks attempted in [run #44528360120](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44528360120); **0 valid predictions and 0 official issues evaluated** |
| Real SWE-bench model issue attempts | Attempt runner and GitHub Actions job available | Pinned pytest task failed proposal validation in [attempt 1](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44495694284) and [attempt 2](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44496682030); no official evaluation or valid benchmark patch |
| SWE-bench model issue resolution rate | Not measured | **N/A — official harness skipped because no valid predictions** |

[Open the recruiter-facing explanation](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/) · [View CI and downloadable run artifacts](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/workflows/repopilot.yml)

## Verified model milestone — November 19, 2026

- [Live Ollama/Qwen 3B verification](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44482479486) fetched [seeded issue #1](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/1), generated a reproduction test and minimal source fix, and proved clean baseline → failing reproduction → passing patched tests in network-restricted Docker.
- [Live model evidence dashboard](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/model-run.html) records the actual run: **35.043 s** end-to-end, **808 provider-reported tokens**. Unambiguous diff formatting was normalized; the model's source-code change was preserved.
- [Draft PR #2](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/2) contains the model-generated fix and regression test. It was opened using connected GitHub access, its CI passed, and it remains **unmerged**.
- This single seeded issue is a controlled integration exercise, **not** an official SWE-bench attempt or generalized agent benchmark.

## Qwen 7B two-file AI candidate — initial verification and review correction (November 19, 2026)

[Real 7B multi-file GitHub Actions run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44538875317) passed **actual model-generated** repairs for [synthetic invoice issue #3](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/3). The model inspected existing source and proposed a patch changing both `pricing.py` and `checkout.py` in **six agent steps**. Static review returned `review_required`; Docker verification returned baseline exit **0**, failing-reproduction exit **1**, and patched-suite exit **0**. The workflow explicitly required `verified=true` and both modified paths before reporting success.

**Review correction:** Inspection of the generated source showed that `pricing.py::taxable_subtotal` still accepted negative inputs directly; only its checkout caller rejected them. The initial reproduction suite failed to test the direct function contract, so the issue is **not yet fully resolved**. An expanded regression suite covering direct negative inputs and rounding now runs in [the stricter CI trial](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44541445489). The earlier successful run is evidence of model-generated source and limited Docker verification, not complete issue correctness.

This is an authentic, **curated synthetic multi-file integration challenge**, not a SWE-bench instance, official score, or evidence of unsupervised reliability on arbitrary repositories. The reproduction tests were supplied as curated challenge tests; only the source patch was generated by the model. Human approval remains required before any new draft PR.

The separate [12-task real-model SWE-bench attempt](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44528360120) processed all 12 pinned issues but exported **0 valid model patches**. Consequently the official harness scoring job was skipped, **0 issues were officially evaluated**, and the resolution rate remains **N/A**, not 0%.

## Current scope

- Parses local Python repositories with `ast`, without importing target code.
- Calls a configured OpenAI-compatible model API to request a **JSON proposal** containing a reproduction test and unified diff.
- Validates the proposed test path and patch path; no arbitrary shell command is accepted from a model.
- Requires a failing reproduction test **before** applying the patch, then a passing test suite **after** applying it.
- Uses an isolated temporary copy and a restricted Docker container with network disabled.
- Produces a local report. The issue-run command does not publish a PR automatically; the separate draft-PR command requires explicit approval. A real model was called in the linked seeded integration run, and the pinned-clone end-to-end command passed in CI; further attempts require provider configuration.
- Provides optional pinned GitHub checkout and ranked source-context selection, with pre-execution review of proposed patch and regression test. These components have CI evidence, including a successful pinned-clone live-model seeded integration; they have not resolved official SWE-bench tasks.
- A GitHub Actions workflow runs unit tests and proves a real sample reproduction fails before the patch and succeeds afterward inside restricted Docker.

[View RepoPilot CI and Docker verification](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/workflows/repopilot.yml)

## Verified integrated end-to-end run — pinned clone

[GitHub Actions run #44497087568](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44497087568) passed the entire supported integration flow: fetch public issue #1 → clone the repository at an immutable commit → select the vulnerable calculator fixture → generate a fix with local Ollama/Qwen2.5-Coder 3B → run static review → verify baseline pass / reproduction fail / patched pass in restricted Docker → save dashboard and evidence as CI artifacts.

This is an intentionally small public issue. It demonstrates **end-to-end operability on the supported fixture**, not reliable autonomy on arbitrary repositories. Human review is still needed to create a draft PR and independent benchmark evaluation is still pending.

## Additional engineering evidence

- **Real model + new review stage:** [GitHub Actions execution](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44495035936) confirms that Ollama generated a fix, static review accepted it for verification, and a restricted Docker test ran baseline green → new reproduction red → patched suite green.
- **Two-file change validation:** The older [Docker CI](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44494911761) verified a human-supplied *reference patch*. Separately, the newer [Qwen 7B live run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44538875317) independently generated a two-file source patch and passed Docker verification against curated regression tests.
- **Real SWE-bench task attempts:** `python -m repopilot.benchmark_attempt INSTANCE_ID --manifest benchmarks/swebench-lite-12.json --output .runs/task-001` loads the official issue text and pinned base revision. It creates an unreviewed candidate or a failure report. See [the GitHub Actions attempt workflow](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/workflows/repopilot-swebench-attempt.yml). A candidate is **not** an official success.
- **Public evaluator integration:** Prediction exporter and result parser check provenance declarations and prevent missing or conflicting outcomes from becoming success claims.

## Full pinned GitHub-to-verified-patch command

The integrated `run-pinned` CLI accepts a public GitHub issue URL and the exact 40-character source commit, clones the public repository, optionally selects a guarded subdirectory, requests a model patch, applies static review and runs baseline/reproduction/regression tests in Docker. It generates a report and dashboard. It does **not** silently publish or merge changes. The approval-gated `draft-pr` command is separate.

```sh
# Requires configured Ollama or compatible model provider, git and Docker
python -m repopilot.cli run-pinned \
  https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/1 \
  FULL_PINNED_COMMIT_SHA \
  --repo-subdir repopilot/fixtures/calculator-buggy \
  --output .runs/github-issue-to-patch
```

The [real GitHub Actions integration workflow](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/workflows/repopilot-ollama.yml) exercises this command against the synthetic issue. Any measured model outcome should be taken from the corresponding completed CI run, not inferred from the existence of the workflow.

## Controlled retry loop

The `run-repair` command provides up to three bounded model proposals. It retains each proposal, applies static review, uses the existing restricted verifier, and produces a review dashboard. The retry logic has automated tests; it has **not** been verified on arbitrary SWE-bench tasks.

```sh
# On a trusted, disposable worker with an already-configured model and Docker:
python -m repopilot.cli run-repair fixtures/calculator-buggy \
  https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/1 \
  --max-attempts 3 --output .runs/retry-issue-1
```

It never automatically merges code or publishes a PR.

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

Select 12 tasks with `select-swebench`, run actual model-generated patches against their pinned base revisions, evaluate with [official SWE-bench tooling](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/evaluation.md), and publish every attempted task, including failures. The reporting module distinguishes reference fixtures and model-generated attempts. The [prediction export](src/repopilot/swebench_export.py) and [official-results import](src/repopilot/swebench_results.py) fail on missing or inconsistent evidence. The [evaluation protocol](benchmarks/README.md) lists task-specific setup requirements. The first actual pinned SWE-bench task attempt for `pytest-dev__pytest-11148` produced **no valid patch** because the small model returned an unsupported patch structure after three tries; GitHub CI preserved the unsuccessful attempt and runtime. **No official SWE-bench score is available yet.**

## Human reviewer checklist

Before publishing a draft PR, verify the GitHub issue, compare the exact local source with its remote revision, inspect the proposed diff for unrelated changes or secrets, review the test's intent, and confirm the restricted container and CI output. The explicit `I_APPROVE_DRAFT_PR` parameter is a final safeguard, not a substitute for review.

## Recruiter demo

For an accurate 90-second recording and LinkedIn Featured description, see [the recruiter demonstration kit](RECRUITER_DEMO.md).

GitHub Actions produces an artifact named `repopilot-verification-fixture` containing an offline HTML dashboard, verification JSON and an explicitly labeled reference-fixture benchmark report. A real model response or PR appears only after an independently verifiable run.

This project is deliberately distinct from browser simulations. Real model inference and Docker verification are demonstrated for **two synthetic integration issues**, including a real 7B multi-file source patch. The 12 genuine SWE-bench tasks were attempted without a valid exported patch; no official resolution rate is measured.
