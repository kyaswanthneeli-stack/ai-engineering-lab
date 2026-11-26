# RepoPilot security policy and threat model

## Supported deployment boundaries

**RepoPilot v2.2.0 is a human-supervised Python CLI, not an authenticated
multi-tenant web application or fully autonomous production repair service.**
Do not expose it on a public HTTP endpoint. Do not use its model-generated
patches without human review and trusted sandbox verification.

* **Input trust:** Public GitHub issue bodies, upstream repository files,
  proposed code and model output are untrusted. They must never be treated as
  shell commands, instructions to change approval policy, or authority to
  choose network destinations or Docker images.
* **Execution boundary:** The tested repair pipeline runs its fixed Python
  unittest command in a networkless Docker container using `--read-only`,
  `--cap-drop=ALL`, `--security-opt=no-new-privileges`, non-root UID,
  PID/memory/CPU limits, an ephemeral `/tmp` and bounded timeouts. **Docker is
  still a powerful host capability.** Only run it on a disposable, isolated
  worker with appropriately restricted GitHub permissions.
* **Deployed CLI image:** `container/Dockerfile.cli` is unprivileged and
  suitable only for **read-only CLI use** (index, graph, offline dashboard
  display). It intentionally has no Docker daemon or mounted socket. **Never
  mount `/var/run/docker.sock` into it** and never inject GitHub credentials
  into public or demo image runs. Full issue-to-patch verification must run
  on a separate trusted, Docker-capable operator machine.
* **PR permissions:** Publishing a draft PR requires exact
  `--approve I_APPROVE_DRAFT_PR`, matching verification evidence, and a
  scoped GitHub token. The publisher reads the changed files and checks
  the reproduction path against the same pinned GitHub commit it uses as
  the draft branch parent. Use reports produced on a trusted worker and
  retain their original artifacts for review.
* **Secrets:** Store tokens in an operator's secure environment/secret
  manager, not in `.env.example`, command lines, committed JSON or dashboards.
  The pipeline's error records use sanitized failure categories rather than
  raw provider exception bodies. Treat source code, issue descriptions and
  artifacts as potentially sensitive even when sanitized.
* **Network:** Public GitHub issue retrieval and explicitly configured model
  endpoints require network access on the operator host. Sandbox test
  execution has networking disabled. Do not pass private repositories or
  secrets to remote models without explicit data-use approval.
* **Supply chain:** Versioned build output is verified in CI. Container base
  images and transitive dependencies need periodic security scanning and
  digest updates before broader distribution.

## Reporting a vulnerability

Do not post credentials, exploit payloads, or private repository data in a
public GitHub issue. Prefer GitHub's private **Report a vulnerability**
mechanism on the repository Security tab, where enabled. If private reporting
is unavailable, contact the repository maintainer privately through an
existing trusted channel. Do not assume a security response SLA exists.

## Limitations and non-goals

There is no hosted API authentication, authorization, tenant isolation,
public job queue, durable service database, or production uptime guarantee.
The public SWE-bench Lite subset has an independently verified baseline of
**1/12 resolved (8.3%)** in v10; fixture test passes do not make the agent
reliably autonomous. Do not use this candidate release for unreviewed
changes to critical systems.
