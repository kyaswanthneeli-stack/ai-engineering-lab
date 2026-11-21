# RepoPilot v2.2.0 stable-release handoff

**Published November 21, 2026:** [stable v2.2.0](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.2.0). [Release evidence](RELEASE_EVIDENCE_v2.2.0.md) records the final workflow, assets, hashes and image digest.

## Gate A — model performance evidence (reviewed; accuracy target open)

The [unassisted v11 12-case trial](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44914670302)
has finished with **0/12 model patches**; official scoring was skipped.
Ten attempts encountered local Ollama timeout/communication errors and
two exhausted the agent budget. [Original audited report](../benchmarks/OFFICIAL_V11_7B_2026-11-21.md).
Do **not** call this a new official 0/12 score or claim **2/12**:
the independently verified fixed-cohort baseline remains **1/12** from v10.
Separately, human-assisted Django **1/1** does not count toward v10.

A **stable supervised CLI distribution can be published with honest
limitations** while the 2/12 autonomous accuracy goal remains an R&D
milestone. Before another costly full-cohort trial, first prove actual
local-model throughput and patch generation on one unassisted task with
a CPU-suitable model.

## Gate B — merge supervised engineering changes

Review and merge [PR #63](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/63) only after all required checks, actual run artifacts and source provenance are reviewed. Existing successful checks are evidence of software functionality, not equivalent to official SWE-bench resolution.

## Gate C — version and release workflow

Review and merge this separate staging release PR **after** PR #63 and its audited v11 failure report. The staging branch has already bumped `pyproject.toml`, the runtime `__version__`, and the read-only CLI Docker image to `2.2.0`; reconfirm the merged version identity and rerun all tests after PR #63 lands. Leave the historical immutable release workflows and v2.2.0rc1 tag intact.

The [version-specific stable-release workflow](../../.github/workflows/repopilot-v2-2-stable-release.yml) is **main-only, gated first-merge trigger and optional manual recovery**. Its runtime identity check requires the consistent `2.2.0` version; the release notes disclose the actual v11 failure and benchmark limits, and a preexisting stable tag or release fails closed. It builds tests, restricted Docker checks, the wheel/sdist, a clean offline install and the sandboxed non-root CLI image before any GHCR or GitHub Release mutation. The GHCR image is commit-SHA-tagged; existing tags/releases are refused.

## Gate D — final verification

Record the new GitHub Actions release run, the stable release URL,
SHA-256 of wheel/sdist, the immutable OCI digest, and successful clean
installation. Validate the public recruiter demo, up-to-date README,
deployment restrictions, known limitations and rollback guide.
Never advertise an unattended production repair service, or a 2/12 solve
rate without a comparable, independently verified result.

**Release disposition:** PR #63 and PR #64 merged; [main publication workflow](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44923164974) succeeded and the stable release is live. The accuracy goal remains an independent R&D gate, not an achieved 2/12 result.
