# RepoPilot — Evidence-first autonomous coding harness

**Stable release: [RepoPilot v2.2.0](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.2.0).** Published November 21, 2026, from commit `5669ea72162c` after [348 unit tests and distribution gates](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44923164974) passed. Versioned wheel and source archive, clean installation, restricted Docker fail-before/pass-after verification and a networkless non-root CLI image are available. [Verified release evidence](docs/RELEASE_EVIDENCE_v2.2.0.md) · [release notes](RELEASE_NOTES_v2.2.0.md) · [deployment](docs/DEPLOYMENT.md) · [operations](docs/OPERATIONS.md) · [security](SECURITY.md) · [live demo](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/recruiter-demo.html).

**Accuracy scope:** The v2.3 rerun resolved **1/12 (8.3%)** of the independently evaluated fixed cohort, matching the v10 baseline. The official harness scored all seven submitted patches and resolved one. The unassisted 7B v11 experiment generated zero valid patches and was unscored; the separately human-assisted Django 1/1 result is not additive. [Benchmark evidence](benchmarks/README.md) · [v11 diagnostic report](benchmarks/OFFICIAL_V11_7B_2026-11-21.md). This is a tested, human-supervised Python repair CLI, not an unattended production SaaS. The OCI image supports read-only indexing and evidence inspection; live repair requires a separate trusted Docker-capable operator worker.

**For Upwork clients:** [Portfolio-ready project case study, deliverables and demonstration script](UPWORK_PORTFOLIO.md). This document distinguishes verified results from experimental capabilities and includes copy suitable for an Upwork portfolio item.

**RepoPilot v2.0 portfolio handoff:** [Verified v2.0 release notes](RELEASE_NOTES_v2.0.0.md) summarize the merged implementation, **185 release-gate Python tests passed, 82% coverage**, official Nov 20 **1/6 submitted and 1/12 selected** benchmark score, and limits. The [one-time v2.0.0 release workflow](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/workflows/repopilot-v2-release.yml) verifies official evidence, unit tests, restricted Docker and package files before it publishes the [immutable release](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.0.0). Check the workflow and release page to confirm publication.

## Current implementation status (verify before citing)

| Capability | Current implementation | Publicly demonstrated |
|---|---|---|
| Python AST indexing and issue-aware bounded context | Built | Ranked context and safety unit tests in GitHub Actions; model used a simpler context in the prior verified seeded run |
| Model proposal over OpenAI-compatible API | Built | Real Ollama Qwen2.5-coder:3b produced a fix and regression test for seeded issue #1; [verified CI run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44482479486) |
| Public GitHub issue retrieval and opt-in pinned clone | Built | [Actual end-to-end live model + pinned clone + Docker CI](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44497087568) passed |
| Issue → proposal → restricted Docker verification | Built | Real model-generated fix passed baseline/reproduction/patched Docker sequence for one seeded integration-test issue; separate reference-patch verification also passes |
| Static pre-execution review and Docker verification | Built | Static review unit tested; still requires human judgment on real patches |
| Offline dashboard and execution-event report | Built | [Interactive recruiter walkthrough](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/recruiter-demo.html), [real Ollama sample](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/model-run.html), and reference-patch dashboard |
| Approval-gated draft PR via GitHub API | Built | [PR #10](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/10) is **merged** after review corrections to a real Qwen 7B two-file model candidate; the corrected result passed CI and restricted Docker checks. Do not attribute the subsequent corrections entirely to the model. Earlier seeded [draft PR #2](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/2) remains unmerged |
| 12 SWE-bench Lite task preparation and result import | Built | All 12 pinned tasks attempted; four model-generated patches submitted and evaluated by the official harness |
| Real SWE-bench model issue attempts | Bounded single and 12-task model runners available | [Baseline 12-task batch](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44547336463) yielded six patches and six timeouts; the [later Nov 19 run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44580636292) yielded four submitted patches and 1 official resolution. The [evidence recovery run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44558575315) preserved the baseline results. |
| SWE-bench model issue resolution rate | Official v2.3 rerun | 1/12 selected (8.3%) and 1/7 evaluated (14.3%). The resolved issue was `sympy__sympy-14774`. [Results](benchmarks/README.md) |

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
- Produces a local report. The issue-run command does not publish a PR automatically; the separate draft-PR command requires explicit approval. A real model was called in the linked seeded integration run, and the pinned-clone end-to-end command passed in CI; further attempts require provider configuration.
- Provides optional pinned GitHub checkout and ranked source-context selection, with pre-execution review of proposed patch and regression test. These components have CI evidence, including a successful pinned-clone live-model seeded integration; the benchmark system has also independently resolved one real SWE-bench Lite task with an official harness result.
- A GitHub Actions workflow runs unit tests and proves a real sample reproduction fails before the patch and succeeds afterward inside restricted Docker.

[View RepoPilot CI and Docker verification](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/workflows/repopilot.yml)

## Verified integrated end-to-end run — pinned clone

[GitHub Actions run #44497087568](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44497087568) passed the entire supported integration flow: fetch public issue #1 → clone the repository at an immutable commit → select the vulnerable calculator fixture → generate a fix with local Ollama/Qwen2.5-Coder 3B → run static review → verify baseline pass / reproduction fail / patched pass in restricted Docker → save dashboard and evidence as CI artifacts.

This is an intentionally small public issue. It demonstrates **end-to-end operability on the supported fixture**, not reliable autonomy on arbitrary repositories. Human review is still needed to create a draft PR and the separate official SWE-bench benchmark now reports one resolved issue out of four evaluated submissions.

## Additional engineering evidence

- **Real model + new review stage:** [GitHub Actions execution](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44495035936) confirms that Ollama generated a fix, static review accepted it for verification, and a restricted Docker test ran baseline green → new reproduction red → patched suite green.
- **Two-file model-generated repair:** [Qwen 7B live GitHub Actions evidence](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44540507015) confirms an initial model-generated patch to `pricing.py` and `checkout.py` passed network-restricted Docker regression. After correcting the direct pricing-API validation and adding tests during review, [PR #10 was merged](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/10). This is a controlled issue, not a SWE-bench task.
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

## Setup preflight (v2.1.0 and later)

Check local prerequisites before any real issue-to-fix attempt. The default
command is **read-only and offline**: it does not invoke Docker, contact a
model provider, or execute repository code.

```bash
cd repopilot
python -m pip install -e .
python -m repopilot.cli doctor
```

For a live local readiness check, start Docker and Ollama and install
the chosen model first:

```bash
export REPOPILOT_BASE_URL=http://127.0.0.1:11434/v1
export REPOPILOT_MODEL=qwen2.5-coder:3b
python -m repopilot.cli doctor --live
```

The `--live` command checks the Docker daemon and reads only the local
Ollama `/api/tags` model inventory. It does not run a model, fetch issues,
or evaluate patches. Remote HTTPS provider endpoints are **not contacted**
and are explicitly **unverified**. `--live` exits nonzero when any required
local check is missing or unverified. The diagnostic is not proof of
correctness or production readiness.

## Local usage

The v10 benchmark used source revision `8388139a219d72801f1c06a76ae9a7cd10e821c7`. The downloadable v2.2.0rc1 packages predate the v10 validation changes. To install the evaluated revision in a fresh directory, use Python 3.11 or newer:

```sh
git clone https://github.com/kyaswanthneeli-stack/ai-engineering-lab.git repopilot-v10
cd repopilot-v10
git checkout --detach 8388139a219d72801f1c06a76ae9a7cd10e821c7
cd repopilot
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

From that directory, run the tests and index the sample. Generating a proposal requires a running model provider. Verification requires Docker.

```sh
python -m unittest discover -s tests -v
python -m repopilot.cli index examples/calculator
export REPOPILOT_BASE_URL=http://127.0.0.1:11434/v1
export REPOPILOT_MODEL=your-local-model
python -m repopilot.cli propose examples/calculator examples/issue.txt --output .runs/proposal.json
# Read the generated patch and test before continuing.
python -m json.tool .runs/proposal.json
docker pull python:3.12-alpine
python -m repopilot.cli verify examples/calculator .runs/proposal.json --output .runs/verification.json
python -m repopilot.cli dashboard .runs/verification.json --output .runs/dashboard.html

# Optional fixture check using the bundled reference patch (requires Docker only).
python -m repopilot.cli verify examples/calculator examples/issue.json --output .runs/reference-verification.json

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

For remote providers, set `REPOPILOT_BASE_URL`, `REPOPILOT_MODEL`, and `REPOPILOT_API_KEY` via environment variables.

**Historical v5 workflow (Nov 20):** [run #44703057273](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44703057273) used loopback-only native Ollama JSON mode (`REPOPILOT_OLLAMA_NATIVE=1`), a 110-second per-request timeout, and a 270-second agent-step budget inside a 300-second per-task timeout. It produced six predictions from twelve attempts and the independent official evaluator resolved one: **1/6 submitted; 1/12 selected**. [Audited report](benchmarks/OFFICIAL_EVALUATION_2026-11-20.md). The improvements did not increase the selected-cohort resolution count. [The Nov 20 single-task run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44700767322) failed with `Local Ollama native chat failed or timed out` after approximately 80 seconds; it generated **no** valid candidate and received **no** official score. The later Nov 19 official run submitted four candidates and resolved one (1/4 evaluated, 1/12 selected), compared with the preserved historical baseline (1/6 evaluated, 1/12 selected). Do not combine these denominators or claim new improvement.

**Optional agent wall-clock budget:** `REPOPILOT_AGENT_BUDGET_SECONDS` accepts `0` (default, disabled) or 10–3600 seconds. Before each agent step RepoPilot checks elapsed time and stops with a recorded error rather than starting a new model call after the budget expires. This is not a hard process timeout: a request already running may finish after the limit and still needs an independent HTTP timeout or external worker deadline. The single-task SWE-bench attempt workflow uses a 600-second agent budget; resolution improvement must be measured separately. Never commit keys. **Only connect to trusted model endpoints**.

**Bounded model calls:** set `REPOPILOT_PROVIDER_TIMEOUT_SECONDS` to an integer from `10` to `120` (default `120`). The value caps each native Ollama or OpenAI-compatible HTTP request, not the entire agent run; timed-out attempts remain failures, never successes. For a **local loopback Ollama** endpoint (`http://127.0.0.1:11434/v1`) without API tokens, `REPOPILOT_OLLAMA_NATIVE=1` opts into Ollama's native JSON API to avoid compatibility-mode stalls. The real single-task SWE-bench attempt workflow opts into native mode and a 75-second request cap, but this is **not** evidence of higher official resolution accuracy. Never commit keys. **Only connect to trusted model endpoints**.

## Threat model and limits

Repository data and issue text are untrusted. Generated patches are never automatically approved. Docker provides defense in depth, not hardened hostile-code isolation. Run verification only on disposable worker machines, without host credentials or Docker socket mounts. Network is disabled within the container; image is pre-pulled. Container timeouts may require manual worker disposal if daemon cleanup fails.

Opt-in pinned public GitHub repository checkout is implemented. There is **no arbitrary-revision automatic cloning** and no unattended merging. GitHub issues can be read via the public REST API. The draft PR CLI publisher's external API route remains mocked in tests. Separately, the authenticated GitHub connector created [real draft PR #2](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/2), CI passed, and it remains unmerged. Separately, the reviewed multi-file PR #10 and agent reliability PR #12 were both merged into main in the v1.0.0 release work. The official SWE-bench harness result of one resolved issue out of four submitted patches is separately documented; no general cost or token savings are claimed.

## Benchmark policy

**Official v10 evidence.** RepoPilot attempted 12 pinned issues and submitted four patches. The official harness resolved one issue, marked three unresolved and recorded zero evaluator errors. Eight attempts produced no submission. [Results and artifacts](benchmarks/README.md).


The official [SWE-bench Lite](https://github.com/SWE-bench/SWE-bench) dataset has 300 issue/patch pairs. Its official evaluation harness requires task-specific environments and regression tests; passing RepoPilot's tiny calculator fixture does not mean a SWE-bench instance is resolved.

Select 12 tasks with `select-swebench`, run actual model-generated patches against their pinned base revisions, evaluate with [official SWE-bench tooling](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/evaluation.md), and publish every attempted task, including failures. The reporting module distinguishes reference fixtures and model-generated attempts. The [prediction export](src/repopilot/swebench_export.py) and [official-results import](src/repopilot/swebench_results.py) fail on missing or inconsistent evidence. The [evaluation protocol](benchmarks/README.md) lists task-specific setup requirements. The [first complete 12-task batch](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44528360120) produced no valid model predictions and was unscored. The **later [12-task run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44547336463)** submitted six authentic model patches, with six timed-out tasks. The official evaluator resolved **`sympy__sympy-14774`** and marked the other five submitted predictions unresolved, with zero evaluation errors. The [successful recovery run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44558575315) archived official results after an initial artifact filename error; the [official score record](benchmarks/OFFICIAL_EVALUATION_2026-11-19.md) documents the distinction between evaluated and selected denominators.

## Human reviewer checklist

Before publishing a draft PR, verify the GitHub issue, compare the exact local source with its remote revision, inspect the proposed diff for unrelated changes or secrets, review the test's intent, and confirm the restricted container and CI output. The explicit `I_APPROVE_DRAFT_PR` parameter is a final safeguard, not a substitute for review.

## Recruiter demo

For an accurate 90-second recording and LinkedIn Featured description, open the [interactive recruiter walkthrough](recruiter-demo.html) and the [recruiter demonstration kit](RECRUITER_DEMO.md).

GitHub Actions produces an artifact named `repopilot-verification-fixture` containing an offline HTML dashboard, verification JSON and an explicitly labeled reference-fixture benchmark report. A real model response or PR appears only after an independently verifiable run.

This project is deliberately distinct from browser simulations. Real provider inference and Docker verification have been demonstrated for a seeded issue and a **controlled two-file invoice issue** subsequently reviewed and merged as PR #10. The [v10 evaluation](benchmarks/README.md) resolved one of four submissions from twelve attempts.
