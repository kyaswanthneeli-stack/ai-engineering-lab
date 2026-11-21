# RepoPilot v2.2.0 — published stable release evidence

**Published:** 21 November 2026, 16:12 UTC.
**Source revision:** `5669ea72162c488dbd806c63bfe6d07c4cf1b990`.

- [Stable GitHub release](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.2.0) (not draft, not prerelease).
- [Successful final main release workflow](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44923164974) and [original CI artifact](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44923164974/artifacts/14714542828).
- [Main repository CI](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44923164939) passed; [Pages deployment](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44923164056) passed.
- [Engineering PR #63](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/63) and [release PR #64](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/64) merged.
- [Recruiter demo](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/recruiter-demo.html).

## Distribution provenance

GitHub release asset metadata reports the following SHA-256 digests:

| Asset | SHA-256 |
|---|---|
| repopilot-2.2.0-py3-none-any.whl | `74b7dac039728a51f0fbce5a2cbd9c65947dda5b1b1d4fe664bd697bf761cff9` |
| repopilot-2.2.0.tar.gz | `a633c7d811e86a1513df4f70b7a7f26840f7b78908476d17c00e286538848aa2` |

OCI image: `ghcr.io/kyaswanthneeli-stack/repopilot:sha-5669ea72162c`.
Published registry image digest (release log):
`sha256:52bae5592314f51e2bf860a98d6ebb8e49ad92142fb7c3e331c26f72c7deade6`.
Registry visibility may require authenticated access.

## Release gates

The successful publication workflow ran **348 Python unit tests**, restricted Docker baseline-pass / reproduction-fail / patched-pass verification, clean offline wheel installation, and non-root network-disabled read-only OCI indexing. The release build pushed the commit-tagged image before publishing the immutable versioned GitHub release. These attest to the tested supervised distribution, not autonomous repair accuracy.

## Reproduce installation

Download the wheel from the [release assets](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.2.0), verify its SHA-256 against the table, and in a clean Python 3.11+ environment run:

```bash
python -m pip install --no-index --no-deps ./repopilot-2.2.0-py3-none-any.whl
python -m repopilot.cli doctor
python -m repopilot.cli --help
```

See [deployment guide](DEPLOYMENT.md) for the trusted operator worker and Docker verification, [security](../SECURITY.md) for boundaries, and [operations](OPERATIONS.md) for rollback.

## Accuracy and scope

The last comparable independently scored fixed 12-task SWE-bench Lite cohort remains **v10 1/12 (8.3%)**. The v11 experiment yielded zero predictions and was not scored. Separate assisted Django 1/1 is not additive. See [v11 failure report](../benchmarks/OFFICIAL_V11_7B_2026-11-21.md) and [assisted evidence](../benchmarks/DJANGO_ASSISTED_7B_2026-11-21.md).

The portfolio-ready supervised CLI is released; higher measured autonomous accuracy and an unattended production service remain separate, unverified goals. Do not advertise multi-tenant SaaS or a new 2/12 score.
