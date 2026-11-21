# RepoPilot v2.2.0 stable-release handoff

**Prepared 21 November 2026. No stable v2.2.0 release has been published
by this staging PR.** The public portfolio prototype is already available as
stable v2.1.1 and prerelease v2.2.0rc1.

## Gate A — model performance evidence

Wait for [unassisted 12-case v11 run #44914670302](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44914670302) and its official evaluator. Preserve its authentic attempt records, original predictions, independent report, provenance hashes and exact unresolved/submitted counts. Compare **resolved/12**, not resolved/submitted. The previous score is **1/12**. The separately assisted Django 7B **1/1** cannot be treated as a second autonomous fixed-cohort success. If v11 is below **2/12**, report the shortfall and prioritize the highest-impact verified failure; do not falsify a release claim.

## Gate B — merge supervised engineering changes

Review and merge [PR #63](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/63) only after all required checks, actual run artifacts and source provenance are reviewed. Existing successful checks are evidence of software functionality, not equivalent to official SWE-bench resolution.

## Gate C — version and release workflow

Review and merge this separate staging release PR **after** PR #63 and its final score notes. The staging branch has already bumped `pyproject.toml`, the runtime `__version__`, and the read-only CLI Docker image to `2.2.0`; reconfirm the merged version identity and rerun all tests after PR #63 lands. Leave the historical immutable release workflows and v2.2.0rc1 tag intact.

The [version-specific stable-release workflow](../../.github/workflows/repopilot-v2-2-stable-release.yml) is **manual-only and main-only**. Its runtime identity check requires the consistent `2.2.0` version; the separate draft-release-notes guard still blocks publication until final score evidence and notes are ready. It builds tests, restricted Docker checks, the wheel/sdist, a clean offline install and the sandboxed non-root CLI image before any GHCR or GitHub Release mutation. The GHCR image is commit-SHA-tagged; existing tags/releases are refused.

## Gate D — final verification

Record the new GitHub Actions release run, the stable release URL,
SHA-256 of wheel/sdist, the immutable OCI digest, and successful clean
installation. Validate the public recruiter demo, up-to-date README,
deployment restrictions, known limitations and rollback guide.
Never advertise an unattended production repair service, or a 2/12 solve
rate without a comparable, independently verified result.

**Release disposition now:** prepared/staged; blocked by the ongoing
official v11 benchmark and the required reviewed source/version merge.
