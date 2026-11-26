# Final portfolio scope audit — November 22, 2026

## Disposition

RepoPilot v2.2.0 is a published human-supervised Python issue-to-patch CLI and evidence-backed portfolio demonstration. This audit does not claim it is an unattended multi-tenant production service. Improving the autonomous benchmark score is a separate research objective, not a condition of portfolio completion. The immutable released assets have not been changed.

| Gate | Evidence reviewed | Result |
| --- | --- | --- |
| Real inference and coordinated multi-file repairs | [Original model and Docker run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44540507015) | Passed on controlled invoice fixture |
| Human-reviewed GitHub PR | [Merged PR #10](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/10) | Passed after reviewer corrections; no autonomous merge claim |
| Restricted Docker, guarded checkout and static indexing | [Main CI](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44926769554) | Passed |
| Installation, artifact and container distribution | [Release pipeline](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44923164974), [v2.2.0 release](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.2.0) | Passed; wheel and source archive published |
| Public evidence-based demonstration | [Pages deployment](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44926769380), [Recruiter demo](https://kyaswanthneeli-stack.github.io/ai-engineering-lab/repopilot/recruiter-demo.html) | Deployment passed; recorded walkthrough, not a live inference service |
| Independent selected-cohort measurement | [v10 official run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44814488203) | 1/12 selected; 1/4 submitted resolved; 8 unsubmitted |

The above is a review of actual prior runs and release metadata, not a newly executed live end-to-end model repair. Installation hashes, limitations and exact deployment scope are preserved in [release evidence](RELEASE_EVIDENCE_v2.2.0.md). The curated reproduction tests and reviewer corrections are explicitly documented in the [demonstration kit](../RECRUITER_DEMO.md).

## Confirmed defect and maintenance review

The [compact 7B experiment](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44998179241) returned one genuine but unresolved patch (0/1 resolved, no evaluator errors). It introduced invalid Python indentation, yet the previous static quality gate treated compilation failure as unavailable analysis. The stable source has the same gate. The maintenance PR isolated the compile-regression fix and regression tests (previously validated on the experimental branch) without importing experimental inference settings or localization changes. It checks all modified files and blocks new compile failures in originally compilable Python before candidate smoke/evaluation. Unsupported original syntax remains explicitly unavailable. The source is never executed by this static check. [PR #68](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/68) merged on November 22 after validation. The guard is available on main. The v2.2.0 package predates it. [Post-merge CI](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/45000504033) and [Pages deployment](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/45000504022) both passed.

## Separate research

The [final 7B identifier-localization trial](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44999518132) ended with a transient Ollama error. It produced no eligible patch, so the independent scoring job skipped the task. The comparable v10 result remains 1 of 12 selected issues resolved. PRs #65 and #67 remain experimental. No further full-cohort run is necessary to close the supervised portfolio scope. Do not launch an expensive benchmark without evidence supporting the new configuration. The 16.7% target is not achieved unless a uniform independently scored cohort establishes it.

## Final usage

Use the published v2.2.0 and documented demonstration for recruiter evaluation; disclose the tested fixture, human review, measured baseline and limitations. Production service requirements (auth/tenant isolation, durable queues, secrets/worker isolation, rate limits, observability, recovery and availability) remain outside this release's tested scope.
