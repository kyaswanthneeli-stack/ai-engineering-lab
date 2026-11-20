# RepoPilot v2.2.0rc1 — Deployment-readiness release candidate

**Status: pre-release candidate.** This version packages an independently
testable, constrained CLI distribution and operational safety documentation.
It does **not** establish a production autonomous repair service, guaranteed
completion by a particular date, or higher official SWE-bench solve rates.

## Changes relative to v2.1.1

- Adds optional, bounded candidate smoke tests with trusted offline Docker
  dependencies and conservative baseline/patch comparison; inconclusive
  probes are never counted as successes.
- Adds configurable issue-context reduction for CPU-hosted local models
  (opt-in only), with explicit prompt-length evidence and a separately
  scored small comparison workflow.
- Sanitizes provider error details written to persistent pipeline reports
  to avoid leaking raw exception bodies, credentials or endpoint details.
- Adds a **non-root CLI OCI image** for read-only source indexing and evidence
  viewing, published with a commit-bound GHCR tag only after CI gates.
- Adds deployment instructions, rollback and incident guidance, a documented
  security boundary, and an operator-owned configuration template.
- Keeps generated PRs human-approved and tied to actual verification evidence.

## Gates for distribution

1. `python -m unittest discover -s tests -v`, compile and measured coverage.
2. Restricted Docker real baseline-reproduction-patched verification.
3. Actual nonroot, offline CLI image smoke with no Docker socket or token.
4. Build versioned wheel/sdist and verify package/version provenance.
5. Publish from protected `main` only if prior gates pass; preserve immutable
   commit-specific image tags, artifact SHA-256 and run evidence.

See [Deployment](docs/DEPLOYMENT.md), [Operations](docs/OPERATIONS.md)
and [Security](SECURITY.md). Packaging/version alone does not mean the
deployment supports always-on inference or unattended repository modification.

## Independent model benchmark

The latest independently verified fixed 12-task SWE-bench Lite v9 run
([GitHub Actions](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44776554310))
resolved **1 of 12 selected (8.3%)**, with six genuine patches evaluated.
No improvement over v8 was established. The separate issue-prompt A/B study
is not an official issue-resolution benchmark.
