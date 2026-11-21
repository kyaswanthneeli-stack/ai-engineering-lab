# RepoPilot v2.2.0 — supervised Python repair CLI

**Scope:** Stable supervised CLI release. Distribution, versioned assets and
container-image digest must be verified on the published
[GitHub release page](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.2.0).
These notes alone do not prove that publication succeeded.

RepoPilot is a human-supervised, Python-focused issue-to-patch coding harness.
The CLI supports bounded repository inspection, genuine model-suggested patch
generation, static review, restricted Docker verification, reproducible
execution evidence and approval-gated GitHub draft pull requests. The
container distribution remains a **read-only, unprivileged, networkless CLI
demo**. Model inference and Docker-based verification run separately on a
trusted operator machine.

## New capabilities since v2.1.1

- Operator-supervised retry experiments with measured behavioral feedback
  and fingerprint rejection of already-failed candidate patches.
- Additional regression tests for SQLite shared-file initialization,
  separate persistent test databases and in-memory alias behavior.
- Source-inspection and patch-validation improvements, including optional
  constrained native Ollama edit formats.
- Archived independently scored real-issue evidence and an experimental,
  uniform Qwen2.5-Coder 7B official 12-task evaluation workflow.
- CI-tested distribution, offline wheel installation, restricted Docker
  baseline/reproduction/patched verification, and nonroot OCI indexing.

## What the independent evidence does and does not prove

The **official v10 fixed 12-task SWE-bench Lite benchmark** independently
resolved **1/12 issues (8.3%)** using Qwen2.5-Coder 3B.
A distinct Qwen2.5-Coder 7B **human-assisted** Django case
`django__django-12113` passed six local SQLite checks and independently
resolved **1/1** in the official harness. The latter used operator-supplied
diagnostics and an explicitly scoped source edit. These outcomes **must not
be added** into a fabricated 2/12 autonomous score.

The **unassisted v11 7B** [12-task run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44914670302)
completed with **zero valid predictions**. Ten attempts failed due to
local Ollama communication/timeouts; two expired the agent deadline.
The official evaluator **did not run** (skipped, zero submissions). Therefore
v11 has **no independent resolution score** and cannot support a 2/12
improvement. [Audited failure report](benchmarks/OFFICIAL_V11_7B_2026-11-21.md)
retains exact original artifact links and hashes. The last real full-cohort
official result remains **1/12 (8.3%)**, measured on v10.

## Stable-release gates

1. Merge verified experiment and benchmark changes after final CI review;
   preserve the source SHA, original scored artifacts and separate human-assisted attribution.
2. Bump `pyproject.toml`, `src/repopilot/__init__.py` and the read-only
   `container/Dockerfile.cli` dependency to `2.2.0` in a reviewed commit.
3. Run the entire unit, restricted-Docker, clean-install packaging,
   unprivileged offline image and source-provenance gates on protected `main`.
4. The **new version-specific** stable release workflow
   `.github/workflows/repopilot-v2-2-stable-release.yml` triggers once
   when first merged into protected `main`, after every gate above.
   Manual dispatch is a recovery option; any preexisting tag or release
   makes the workflow fail closed, without overwriting immutable evidence.
5. Publish the versioned wheel, sdist and SHA-addressed CLI image only after
   successful gates. Record the final CI URL, asset SHA-256 and GHCR digest.
6. Verify the published release, GitHub Pages demonstration, deployment
   guide, rollback instructions, and operator-approved PR workflow.

## Important limitations

RepoPilot does **not** provide an authenticated multi-tenant SaaS, public
inference endpoint, unattended code merging, guaranteed repair accuracy,
durable job queues, service-level availability or disaster recovery.
Deployment requires a trusted human operator for live repair, and generated
PRs require explicit human approval.

Documentation: [deployment](docs/DEPLOYMENT.md) ·
[security](SECURITY.md) · [operations](docs/OPERATIONS.md) ·
[official evaluation](benchmarks/README.md) ·
[recruiter demo](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/recruiter-demo.html).
