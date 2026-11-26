# RepoPilot engineering sprint

Audit started 26 November 2026 from main at commit `35457d5`. The published stable release is [v2.2.0](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/releases/tag/v2.2.0). The sprint uses [existing completion gates](PROJECT_COMPLETION_GATES.md) and [release evidence](RELEASE_EVIDENCE_v2.2.0.md) as its starting point.

| Priority | Component | Confirmed issue and sprint change | Evidence and remaining work |
| --- | --- | --- | --- |
| P1 | Verification workspace | File scanning and workspace copying applied different exclusions. Verification and draft publication now share a copy routine that admits regular files and directories and excludes runtime and dependency output. | Snapshot regression tests cover excluded directories and linked files. Restricted Docker checks run in GitHub Actions. |
| P1 | Draft PR and dashboard evidence | Exit codes alone could be accepted without a valid test run. The publisher and dashboard now require the three recorded unittest stages. Publication compares files against its pinned parent commit and refuses to replace a reproduction file already present there. | Automated checks use recorded test results and a fake GitHub API. A live draft publication requires a disposable target and approval for that target. |
| P1 | Benchmark quality | The comparable v10 cohort resolved **1/12**. Four predictions were evaluated and eight tasks produced no prediction. v11 produced no eligible cohort submissions. The compact preflight evaluated one unresolved patch. | [Audited v10 data](../benchmarks/evidence/v10-audited-evidence.json), [v11 report](../benchmarks/OFFICIAL_V11_7B_2026-11-21.md), [compact preflight](FINAL_PORTFOLIO_AUDIT.md). A pinned, unassisted subset with adequate model compute is still needed to validate any improvement. |
| P2 | Dashboard and deployment | The existing offline dashboard renders supplied evidence. The stable deployment is a read-only CLI image. | Fresh installation, Docker isolation, packaging, small-screen browser rendering, and operator startup instructions are distinct release checks. |
| P2 | Related repositories | AgentGate, RouteWise, CodeAtlas MCP, and SourceDesk are separate repositories with their own integration points and workflows. | Local baseline suites passed. Pinned dependency installations, live deployment checks, and a deeper audit remain separate work. |
| P2 | Distribution | The repository has release artifacts and contribution instructions. The original software and documentation now have an MIT license. | Upstream sources and benchmark material retain their terms. Validate packaging and the release checklist before making a new tag. |

Open benchmark branches reviewed include [Django deadline recovery](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/62), [CPU preflight](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/65), and [compact 7B preflight](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/67). Keep independent evaluator outcomes, assisted subset results, and ordinary tests in separate totals.

## v10 failure investigation

Both [original archives](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44814488203) matched the published SHA-256 hashes. The generation and scoring prediction files were byte-identical. The official result and scorecard hashes also matched the preserved provenance.

| Cases | Confirmed observation | What the evidence leaves open |
| --- | --- | --- |
| Django 12113, 12589, 14730 and SymPy 11870, 20212 | Native Ollama communication-or-timeout failure after roughly 271–272 seconds in each case. No submitted patch. | The records combine transport errors and timeouts, so the underlying cause of each failure is unknown. |
| xarray 4493 and pytest 11148 | The remaining agent deadline expired before a native retry after about 270 seconds. No submitted patch. | The artifacts do not establish that a different time budget would have produced a valid patch. |
| SymPy 13773 | The native provider returned HTTP 500 after about 144 seconds. No submitted patch. | The saved attempt and workflow summary do not establish the provider's internal cause. |
| Django 12125 | The original and candidate passed a module import probe. The official evaluator found the repair unresolved. | Import success could not verify issue behavior. |
| Matplotlib 22835 | The original and candidate passed the issue example in the pinned native runtime. The official evaluator found the repair unresolved. | The example did not distinguish the candidate from the baseline. |
| scikit-learn 12471 | The local module import baseline exited nonzero. A prediction still reached the independent evaluator and remained unresolved. | The local smoke comparison was inconclusive. The evaluator did not record an infrastructure error. |

The first controlled experiment needs a local model worker with enough compute
to complete a bounded, unassisted attempt and preserve separate provider
communication, request timeout, and agent-deadline observations. A controlled
behavior comparison should use a test that distinguishes a known failed
candidate from the pinned original before spending compute on the full cohort.

## Controlled provider retest

[Run 45904411806](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/45904411806) ran the pinned Django SQLite test-database case using Docker and native loopback Ollama on a standard GitHub-hosted Linux runner. The archived Docker/Ollama preflight passed. The runner produced a patch in 50.496 seconds, including a 42.236-second model call. The first discovery request used 22,413 characters and 2,702 prompt tokens. It emitted a candidate after inspecting two symptom-level files. The import probe did not distinguish the original from the candidate.

The independent evaluator recorded **0/1 resolved**, one unresolved and zero evaluator errors. The prediction SHA-256 was `65d12b223491befedd2a62cb530ffc8bc59476eadc1b22cdaed333f785ec7b6b`, byte-identical to the earlier unassisted 3B preflight prediction. The next experiment changes only source ranking and keeps the same case and model configuration. Distinctive words from the issue title can prioritize matching source path components, including names with numeric version suffixes. The original issue, pinned revision, and official evaluator are preserved. The full-cohort score remains **1/12**.
