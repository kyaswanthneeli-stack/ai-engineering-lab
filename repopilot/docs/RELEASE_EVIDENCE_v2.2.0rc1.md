# RepoPilot 2.2.0rc1 — verified release and deployment handoff

**Source revision:** `37d35b4f498da65c0802c89ab128821e8aefffc2`.

The [official release workflow](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44791102579) **completed successfully** on November 20, 2026. This record describes distribution of a **human-supervised CLI**, **not** general-purpose production autonomous repair.

## Release artifacts and deployment

- [Immutable versioned GitHub pre-release](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.2.0rc1): versioned wheel and source archive, published after release gates.
- [GitHub Actions release evidence artifact](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44791102579/artifacts/14656302734): distribution packages, SHA-256 file hashes, measured coverage, regression verification and offline OCI indexing evidence.
- **CLI image:** `ghcr.io/kyaswanthneeli-stack/repopilot:sha-37d35b4f498d`
- **Published image digest:** `sha256:7802c54f9483def141d42ce71e5528e6e575299c4a10b1085329e277005d3b44`
- Registry visibility is **not** guaranteed public; GitHub Packages may require the owner to explicitly enable public visibility. The CI runner authenticated successfully and pushed the image.

## Actual checks

| Gate | Verified result |
|---|---|
| Unit test suite | 282 passed |
| Measured Python coverage | 82% |
| Read-only non-root Docker CLI | Source indexing passed with networking disabled |
| Restricted Docker verification | Original baseline green, bug reproduction red, patched tests green |
| Trusted candidate smoke | Baseline-pass, patched-regression-fail correctly detected |
| Version and package integrity | 2.2.0rc1 package and runtime version consistent |
| Clean wheel installation | Passed without package downloads |
| GHCR image publication | Completed, digest recorded above |
| GitHub prerelease publication | Completed, versioned assets attached |

### Security/operational limits

The container image does **not** expose an HTTP server, mount a host Docker socket, carry credentials or perform unattended repairs. Running issue-to-patch verification still requires an appropriately configured, trusted, Docker-capable operator worker and human approval for draft pull requests. See [deployment](DEPLOYMENT.md), [operations](OPERATIONS.md), [architecture](ARCHITECTURE.md) and [security](../SECURITY.md).

**Independent model accuracy remains 1/12 resolved (8.3%)** on the selected v9 SWE-bench Lite cohort ([official evaluator](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44776554310)). The release-candidate gates demonstrate packaging, tested workflow correctness and a deployable read-only CLI—not 50% bug-solving accuracy, multi-tenant security, high availability, or enterprise production readiness.

## Next actions for the owner

Verify the GHCR package visibility settings if external clients must pull the image, demonstrate the existing Pages walkthrough and released CLI in a clean environment, and keep model accuracy improvements separate from the released candidate. Do not replace this release tag; publish a new version after further changes.
