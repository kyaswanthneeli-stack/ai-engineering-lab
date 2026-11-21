# RepoPilot 2.2.0 stable deployment guide

This is an **operator-supervised CLI**, not an always-on hosted web service.
The container below is for read-only commands. Model-driven patching and
Docker verification require a separate disposable operator worker.

## Deployment modes

| Mode | Can do | Must not do |
|---|---|---|
| OCI / GHCR CLI image | Show help, static Python indexing, static import graph, render offline evidence | No Docker socket, no live repair verification, no unattended PRs |
| Host Python wheel + trusted Docker worker | `doctor --live`, public issue retrieval, pinned checkout, real model proposal, restricted Docker verification, human-approved draft PR | Never run user/model commands or automatically merge PRs |
| GitHub Pages | Existing static recruiter dashboard and examples | No backend API, no model inference, no writable storage |

### Prerequisites

* Trusted Linux or macOS operator machine with Python 3.11+ (3.12 tested),
  Git, Docker with a healthy daemon, and access to an approved model endpoint.
* For local Ollama, keep `http://127.0.0.1:11434/v1` on loopback and explicitly
  install the selected model. Never expose the Ollama endpoint unauthenticated.
* Docker sandbox image `python:3.12-alpine` must be pre-pulled by the operator.
  Optional candidate smoke requires building
  `ci/Dockerfile.candidate-smoke` using developer-maintained dependencies.
* A public GitHub issue URL and the exact 40-character pinned base commit.
  Public repositories are cloned; never reuse a workspace containing secrets.

## A. Read-only container (deployable demonstration)

The release workflow publishes an **immutable-commit-tagged image** to GHCR
only after Python tests and actual Docker checks pass. Find the exact image
tag and digest in the release workflow summary; do not assume a `latest` tag
or that a newly published GitHub package is public. An authenticated pull
may be required until package visibility is explicitly configured.

Build the same image locally without needing a registry:

```bash
cd repopilot
docker build -f container/Dockerfile.cli -t repopilot-cli:2.2.0 .
docker run --rm --read-only --network none --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 64 --memory 512m \
  --cpus 1 --user 65532:65532 \
  -v "$PWD/examples/calculator:/workspace/example:ro" \
  repopilot-cli:2.2.0 index /workspace/example
```

This read-only image intentionally does **not** include Docker access, a model
or a GitHub token; therefore `doctor --live` will not report readiness for
end-to-end repair. **Never mount `/var/run/docker.sock`** into this image.
For a full repair run, use the separate worker mode below.

The published v2.2.0 image is `ghcr.io/kyaswanthneeli-stack/repopilot:sha-5669ea72162c`, digest `sha256:52bae5592314f51e2bf860a98d6ebb8e49ad92142fb7c3e331c26f72c7deade6`. See [release evidence](RELEASE_EVIDENCE_v2.2.0.md) for provenance. Authenticate if registry visibility requires it. Do not assume a mutable `latest` tag.

## B. Full, human-supervised repair on a trusted operator worker

```bash
cd repopilot
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --no-deps .
docker pull python:3.12-alpine
# Optional: build the trusted preinstalled dependencies for model candidate smoke
docker build -t repopilot-candidate-deps:py310 \
  -f ci/Dockerfile.candidate-smoke ci
```

Set credentials and endpoints through your OS credential manager; do not add
real secrets to the repository. See `../.env.example` as a *sample* only.
Local Ollama example:

```bash
export REPOPILOT_MODEL=qwen2.5-coder:3b
export REPOPILOT_BASE_URL=http://127.0.0.1:11434/v1
export REPOPILOT_OLLAMA_NATIVE=1
python -m repopilot.cli doctor --live
```

The live preflight must report `ready_for_verified_workflow: true` before
trying the full supported workflow. Then use a human-selected public issue
and pinned SHA; examples in README are seeded integration exercises:

```bash
python -m repopilot.cli run-pinned \
  https://github.com/kyaswanthneeli-stack/ai-engineering-lab/issues/1 \
  FULL_PINNED_COMMIT_SHA \
  --repo-subdir repopilot/fixtures/calculator-buggy \
  --output .runs/run-001
```

Inspect `.runs/run-001/run.json`, `proposal.json`, `verification.json` and
`dashboard.html`. Check before/after test logs; a model's self-assessment is
not verification. Only after **human review** of the exact proposal and
verification evidence should a restricted-scope token be supplied to the
separate `draft-pr --approve I_APPROVE_DRAFT_PR` command. Never give GitHub
write credentials to the Docker test container.

## C. CI, registry publishing and provenance

* `.github/workflows/repopilot.yml` provides Python, Docker, and fixture gates.
* `.github/workflows/repopilot-v2-2-stable-release.yml` published the stable distribution from main after verification; it refuses existing release or image tags. `.github/workflows/repopilot-v2-2-stable-preflight.yml` provides read-only PR packaging checks.
* [Stable release notes](../RELEASE_NOTES_v2.2.0.md) and [published evidence](RELEASE_EVIDENCE_v2.2.0.md) describe the shipped scope.
* Full SWE-bench accuracy remains **1/12 officially resolved (8.3%)** from v10. v11 was unscored; the human-assisted Django subset cannot improve the full-cohort numerator.

## D. Rollback and incident response

1. Stop model-driven runs and disable GitHub write tokens if unsafe or
   unexpected changes appear. Do not merge any generated PR.
2. Preserve immutable local reports and GitHub workflow artifacts while
   redacting credentials before sharing.
3. Roll back the read-only CLI image to the previously verified **SHA tag**
   or the published v2.1.1 wheel. Do not overwrite the old image/tag.
4. Rerun `doctor --live` and the restricted Docker fixture before restoring
   the trusted worker workflow.
5. Investigate failures using `docs/OPERATIONS.md`. A passing build, image
   startup, or fixture test never constitutes official bug-resolution proof.

## What remains before declaring a general production service

Authenticated API / tenant isolation, queue durability, rate limits, supply
chain scanning, observability, disaster recovery drills, live deployment
availability measurements, and a higher independent real-issue solve rate
are **not** demonstrated by this stable CLI release. Do not claim these exist.
