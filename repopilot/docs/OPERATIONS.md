# RepoPilot release-candidate operations and recovery

## Deployment checklist

- [ ] Verify target branch/commit and inspect proposed diff; require human review.
- [ ] CI Python test suite passes with measured coverage (not merely compilation).
- [ ] Restricted Docker regression checks pass on the trusted runner.
- [ ] CLI OCI image builds; a nonroot, networkless, read-only container can index a read-only mounted Python tree.
- [ ] Version recorded in `pyproject.toml` and `src/repopilot/__init__.py`; never silently overwrite a release tag.
- [ ] Confirm published image digest and immutable source commit; GHCR visibility verified by an authenticated operator.
- [ ] No Docker socket, GitHub token, API key, home-directory bind mount, or private repo contents in the demo image.
- [ ] README, deployment guide, security policy and limitations reviewed.
- [ ] Latest official SWE-bench results cited with selected, submitted, evaluated and resolved counts; no inferred successes.
- [ ] Run `doctor --live` on **the operator worker**, not in the read-only demo image, before model-driven changes.

## Supported run and evidence

The operator picks a public GitHub issue URL and **immutable full SHA**. RepoPilot
fetches the issue, inspects Python, obtains a model patch and a reproduction
test, statically checks the proposal, and verifies a bounded fail-before /
pass-after sequence inside network-restricted Docker. The result is a *local
report*, not authority to push anything. Draft PR creation requires explicit
`I_APPROVE_DRAFT_PR` and a scoped GitHub token; merges are always manual.

Every work item should have a unique output directory under `.runs/`.
Treat evidence as write-once. Back up and redact as needed; there is no durable
central job store and no automatic retry coordinator for production requests.

## Failure modes / immediate response

| Signal | Interpretation | Action |
|---|---|---|
| `docker_unavailable`, `container_cleanup_unconfirmed` | Sandbox cannot be trusted | Stop use of worker; check daemon & orphan containers before reusing |
| `baseline_did_not_pass` | Original behavior was not established | Record inconclusive; check pinned dependencies; do not count as regression |
| `TransientOllamaError`, model deadline | Provider could not complete bounded inference | Check local model inventory, CPU/RAM, model logs, and prompt budget; no fabricated patch |
| `no_regression_observed` | Narrow baseline and candidate probe passed | **Not** a solve result; rely on actual reproduction and official evaluation |
| `verified_in_sandbox` | Controlled local regression sequence passed | Human must review patch, scope, test and source before a draft PR |
| GitHub publication denied | Missing approval, token or evidence integrity | Never bypass the approval gate; resolve prerequisites |
| Unexpected secret in JSON/HTML artifacts | Potential data leak | Restrict artifact access, revoke exposed token, review code/CI and re-issue token |
| Official evaluator absent | Model patch never received an official pass/fail | Keep score pending; report submitted/evaluated denominators separately |

## Rollback

Use the prior known-good SHA-tagged container image or published v2.1.1
package. Avoid `latest` tags; don't replace old GitHub Actions artifacts or
overwrite evidence in place. Verify the rollback in CI and on a disposable
operator worker before resuming issue handling.

## Monitoring and service claims

GitHub Actions is the currently tested source of unit-test and fixture evidence.
There is no hosted SaaS process, service-level objective, uptime monitor,
alerts pipeline, customer database, or incident paging. The benchmark
watchers are separate monitoring automations, not a hosted repair service.
Official v9 result: **1/12** selected issues resolved; 6 submitted/evaluated,
5 unresolved and 6 unsubmitted. Future score changes must be independently
scored, not calculated from generated patch count.

## Tomorrow's promotion decision

A release candidate can be promoted to a portfolio distribution only when
the complete test suite, Docker integration, image publish and provenance
checks are green. General autonomous production readiness also needs stronger
model accuracy, security review, and operations capabilities listed above.
Document exact blockers rather than promise calendar-based completion.
