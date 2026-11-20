# RepoPilot — Client portfolio and Upwork presentation kit

> **Project type:** independently developed, public engineering portfolio sample. This is **not** evidence of a completed or paid Upwork contract, a production deployment, or unattended code-fixing guarantees.

## Upwork portfolio item

**Title:** RepoPilot | Python AI Coding Agent with GitHub and Docker Verification

**My role:** Python / AI engineering — architecture, agent workflow, safety, testing, benchmarking, and documentation.

**Description (under Upwork's 600-character portfolio limit):**

Developed RepoPilot, an open-source Python AI coding-agent prototype that turns GitHub bug reports into reviewable patches. It supports bounded source inspection, LLM-generated code changes, regression-test workflows, restricted Docker verification, and human-approved pull requests. Demonstrated real Ollama-generated fixes and a public SWE-bench Lite evaluation. The benchmark covers 12 pinned issues; baseline results were 1 resolved of 6 evaluated patches, not 12/12. Includes source, reproducible tests, CI evidence, and a client-facing walkthrough.

**Skills:** Python, Generative AI, LLM Integration, AI Agents, GitHub Actions, Docker (choose the closest current Upwork skill tags).

**Live walkthrough:** https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/recruiter-demo.html

**Source code:** https://github.com/kyaswanthneeli-stack/ai-engineering-lab/tree/main/repopilot

## Client problem and engineering approach

Teams handling repeated GitHub bug reports need a way to examine candidate fixes, reproduce problems, and gather evidence without accepting arbitrary model-generated patches. RepoPilot is a transparent **prototype** for that workflow, with explicit guardrails and human review.

1. Read a public GitHub issue and select an immutable repository revision.
2. Inspect bounded Python source files through guarded read-only tools.
3. Ask a configured LLM for a candidate patch; reject malformed or out-of-scope proposals.
4. Run a baseline, failing reproduction, and patched regression in a restricted Docker test environment.
5. Save a machine-readable verification report and offline reviewer dashboard.
6. Prepare a draft pull request only with human approval.

## Architecture at a glance

```text
GitHub issue + pinned commit
          |
     Bounded inspection ----> local Ollama / configured compatible model
          |                                |
          +----------------------- candidate JSON / patch
                                           |
                                   Path + diff validation
                                           |
                                Human-reviewable change
                                           |
                             Restricted Docker regression
                                           |
                            Evidence report + dashboard
                                           |
                                 Approval-gated draft PR
```

**Stack:** Python 3.12, Python AST tools, HTTP model integrations (Ollama / OpenAI-compatible), GitHub API / Actions, Git, Docker, JSON/JSONL, unittest, SWE-bench Lite evaluation harness. No LangGraph claim is made for this repository.

## Public, verifiable evidence

- **Real issue-to-fix demonstration:** [pinned-clone and Docker workflow](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44497087568).
- **Real two-file model proposal:** [live Qwen 7B run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44540507015); subsequent human corrections and [merged PR #10](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/10) must not be attributed entirely to the model.
- **Automated testing:** [post-merge main CI](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44703057248) passed. The exact test count and coverage depend on the commit tested.
- **Official benchmark baseline:** [Nov 19 authenticated evidence](benchmarks/OFFICIAL_EVALUATION_2026-11-19.md) recorded 12 selected SWE-bench Lite issues, six submitted model patches, one officially resolved, and five unresolved. This means **1/6 evaluated** and **1/12 selected**. The [later Nov 19 run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44580636292) separately submitted four and resolved one.
- **Nov 20 follow-up:** [live official workflow #44703057273](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44703057273) attempted all 12 pinned issues and generated six candidate patches. Its **official evaluator outcome must be checked** before adding a new score or a resolution claim.
- **Progress tracker:** [v2 release gate](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/16). v2 remains an unreleased engineering milestone until evaluation evidence, review and release gates finish.

## Scope clients could commission

RepoPilot is a demonstration of transferable skills. A client engagement should be scoped to a **specific repository and acceptance criteria**, not sold as guaranteed autonomous repair.

| Engagement | Example deliverable | Explicit boundary |
|---|---|---|
| AI-assisted GitHub issue triage | Issue context extraction, ranked source review and candidate JSON patch | No unreviewed merges |
| Python LLM agent proof of concept | Controlled tool calls, retry/timeout controls, logging and tests | An experimental agent, not production reliability |
| Safe CI repair workflow | Docker test sequence, regression checks, reviewer evidence | Client supplies authorized CI environment |
| AI evaluation harness | Pinned issues, per-task failures, JSONL predictions, validated scorecard | Report observed pass rate, no guaranteed score |

## Ready-to-copy Project Catalog concept

**Service title:** I will build a Python AI agent proof of concept with GitHub and Docker testing

**Project summary:** I develop a scoped Python LLM agent that can inspect permitted repository files, generate reviewable structured proposals, and produce reproducible testing evidence. The deliverable can include a working code sample, Docker-based regression checks, CI workflow, and setup documentation. The design prioritizes bounded tool access, error handling, and human approval before any production change. Supported models, inputs, and acceptance tests are agreed upon before the engagement.

**Suggested milestones:** Requirements and supported repository -> agent and tool integration -> bounded test execution -> walkthrough and handover.

**Client requirements:** GitHub repository link or approved source bundle, sample issue(s), preferred model/provider, operating environment, authorized test commands, expected outputs, data-sensitivity restrictions, and definition of done.

**Do not advertise:** 100% SWE-bench accuracy, autonomous production deployment, unsupported frameworks, fake client results, or a certification.

## 60–90 second walkthrough script

1. Show the public issue and point to the exact pinned repository commit.
2. Open the source-inspection trace and explain the read-only tool boundary.
3. Display the real model-produced candidate for the controlled two-file example.
4. Show the baseline green / reproduced issue red / patched tests green sequence in Docker.
5. Show the reviewer dashboard and explain why approval is required for any pull request.
6. Conclude with the official benchmark's **submitted and selected denominators**, including failures and timeouts. If a newer run remains pending, label it pending.

## Local reproduction

```bash
git clone https://github.com/kyaswanthneeli-stack/ai-engineering-lab.git
cd ai-engineering-lab/repopilot
python -m pip install -e .
python -m unittest discover -s tests -v
```

For the Docker fixture and live Ollama integration, follow [README.md](README.md) rather than running untrusted code on a personal computer. Real inference requires an installed model and an authorized local or secured provider.

## Limitations and terms

Python-oriented proof of concept; real-world issues may fail due to insufficient model quality, dependency gaps, timeouts or ambiguous requirements. Docker restrictions are defense-in-depth, **not** a hardened isolation system for malicious code. No credentials should be put in a public issue, artifact or demo. The repository and CI evidence establish a working prototype and its specific measured results, not a guaranteed enterprise service.
