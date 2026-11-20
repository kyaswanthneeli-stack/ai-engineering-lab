# RepoPilot v2.1.0 — Stable portfolio engineering release

**Release date:** November 20, 2026  
**Source:** [GitHub project](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/tree/main/repopilot) · [Interactive demo](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/recruiter-demo.html) · [Official benchmark report](benchmarks/OFFICIAL_EVALUATION_2026-11-20.md)

RepoPilot is a **Python-oriented, evidence-first coding agent prototype** that takes GitHub issues, inspects bounded source code, requests a model-generated proposal, verifies selected changes in a restricted Docker test environment, and preserves a human approval gate before publishing draft pull requests. It is suitable as a tested engineering portfolio project, not a guarantee that arbitrary repository issues can be repaired.

## What changed since the published v2.0.0 release

- **Large-repository inspection:** replaced unbounded recursive globbing with entry-budgeted directory traversal; prioritizes explicit issue paths without traversing the entire repository ([PR #26](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/26)).
- **Model tool security:** excluded virtual environments, dependency and build directories, Git internals and run artifacts from both indexed and direct issue/model-directed file reads; rejects symlinked parent traversal ([PR #27](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/27)).
- **Predictable context limits:** file-truncation notices are included inside the configured source-context character budget ([PR #27](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/27)).
- **Safe setup diagnostics:** `python -m repopilot.cli doctor` inspects prerequisites without network or subprocess calls; `python -m repopilot.cli doctor --live` additionally performs bounded Docker daemon and **localhost Ollama-only** model inventory checks. External HTTPS provider access remains explicitly unverified, not silently contacted ([PR #28](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/28)).
- **Verification:** CI runs the full Python suite, a reference bug reproduction and its patch in restricted Docker, checks the immutable official benchmark evidence, builds wheel and source artifacts, and smoke-tests the newly built wheel in a clean virtual environment.

## Authentic official benchmark evidence (unchanged from v2.0.0)

The [November 20 official SWE-bench Lite run #44703057273](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44703057273) attempted **12 pinned issue tasks**, generated **6 authentic model patches**, and independently evaluated those six with the official harness: **1 resolved, 5 unresolved, 0 evaluator errors**. The other six tasks produced no prediction (three timeouts and three model/tool failures). This is **1/6 submitted = 16.7%**, or **1/12 selected = 8.3%**. This sample is **not** a general SWE-bench success rate and does not show improvement over the November 19 baseline.

Source evidence is preserved in [the per-task report](benchmarks/OFFICIAL_EVALUATION_2026-11-20.md), [official JSON](benchmarks/official-score-2026-11-20.json), [six model patches](benchmarks/official-predictions-2026-11-20.jsonl), and SHA-256 integrity regression checks. No new official model benchmark was run to validate the impact of v2.1.0's fixes.

## Getting started

```bash
git clone https://github.com/kyaswanthneeli-stack/ai-engineering-lab.git
cd ai-engineering-lab/repopilot
python -m pip install -e .
python -m repopilot.cli doctor
python -m unittest discover -s tests -v
```

After installing a supported local Ollama model and starting Docker:

```bash
export REPOPILOT_BASE_URL=http://127.0.0.1:11434/v1
export REPOPILOT_MODEL=qwen2.5-coder:3b
python -m repopilot.cli doctor --live
```

Read [README.md](README.md) for bounded `run-pinned`, `run-repair`, static graph, dashboard and approval-gated draft-PR usage. The local `doctor` preflight cannot verify a model's fix correctness, Docker is defense-in-depth rather than a hardened hostile-code environment, and live workflows still require safe disposable workers and human review.

## Publication gates

Versioned release assets are published **only if** the automated v2.1.0 workflow completes: all Python unit tests, coverage report, unchanged official benchmark validation, Docker regression, package build, offline setup diagnostic, clean-venv wheel smoke test, and immutable-release existence checks. The [v2.1.0 GitHub release page](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.1.0) and its workflow results are the source of truth for actual publication.

**Scope:** source code, distributable Python package, bounded AI-agent workflow, local verification dashboard, official benchmark report, tests, and client-facing demo. No unattended production deployment, automatic merges, universal repository support, manufactured client history, or performance guarantees.
