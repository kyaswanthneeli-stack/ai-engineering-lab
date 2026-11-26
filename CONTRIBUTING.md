# Contributing to the AI Engineering Lab

Open an issue describing the user-visible behavior, the affected commit, and the smallest input that reproduces the problem. For RepoPilot, include the Python version and whether Docker or a local model was involved. Redact provider credentials, private repository paths, and sensitive logs. For a security report, follow [RepoPilot's security policy](repopilot/SECURITY.md).

## RepoPilot checks

From the repository root, use Python 3.11 or later in an isolated environment.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ./repopilot
(cd repopilot && python -m unittest discover -s tests)
node --test
```

The JavaScript suite covers the browser lab. On a machine with Docker, use the [RepoPilot workflow](.github/workflows/repopilot.yml) for the container and dependency-aware checks. Model calls and Docker verification have separate prerequisites in the [RepoPilot README](repopilot/README.md). Test controlled fixtures locally before relying on external repository behavior.

## Pull requests

Describe the user-visible change, the verification commands you ran, and any remaining failure cases. Keep issue fixture, model candidate, and reviewer edits distinguishable in the evidence. Report which regression ran before and after the patch.

For benchmark updates, link the pinned manifest, generation and scoring artifacts, commit, model, and run ID. Report selected, submitted, evaluated, unresolved, error, and unsubmitted counts. The selected-cohort and evaluated-patch rates answer different questions. See the [benchmark protocol](repopilot/benchmarks/README.md).
