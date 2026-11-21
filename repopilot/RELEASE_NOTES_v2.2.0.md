# RepoPilot v2.2.0 — supervised Python repair CLI

**Release stage:** prepared, **not yet published**. This document is a release
candidate draft for an eventual stable `v2.2.0` tag; it is not evidence that
the tag, wheel, source archive, or container image has been released.

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

The new **unassisted 12-task v11 7B** run
[GitHub Actions #44914670302](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44914670302)
must complete with independently validated predictions, full-cohort
denominators, evaluator errors and preserved SHA-256 provenance before a new
autonomous score can be claimed. Update the benchmark evidence with its
actual outcome **before publication**. A green GitHub workflow is not a
positive SWE-bench resolution on its own.

## Stable-release gates

1. Merge verified experiment and benchmark changes after final CI review;
   preserve the source SHA, original scored artifacts and separate human-assisted attribution.
2. Bump `pyproject.toml`, `src/repopilot/__init__.py` and the read-only
   `container/Dockerfile.cli` dependency to `2.2.0` in a reviewed commit.
3. Run the entire unit, restricted-Docker, clean-install packaging,
   unprivileged offline image and source-provenance gates on protected `main`.
4. Manually dispatch the **new version-specific** stable release workflow
   `.github/workflows/repopilot-v2-2-stable-release.yml` from `main`.
   It must refuse an existing tag or image; never overwrite immutable evidence.
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
