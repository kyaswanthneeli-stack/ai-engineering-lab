# RepoPilot — Evidence-first autonomous coding harness

RepoPilot is an independent Python engineering project exploring issue-to-patch automation. The source is inspectable, with explicit trust boundaries and tests.

## Current scope

- Parses local Python repositories with `ast`, without importing target code.
- Calls a configured OpenAI-compatible model API to request a **JSON proposal** containing a reproduction test and unified diff.
- Validates the proposed test path and patch path; no arbitrary shell command is accepted from a model.
- Requires a failing reproduction test **before** applying the patch, then a passing test suite **after** applying it.
- Uses an isolated temporary copy and a restricted Docker container with network disabled.
- Produces a local report. **No GitHub PR is created; no model call is performed without configuration.**

## Local usage

Python 3.11+ and Docker are required for the full workflow.

```sh
cd repopilot
python -m unittest discover -s tests -v
python -m repopilot.cli index examples/calculator
export REPOPILOT_BASE_URL=http://127.0.0.1:11434/v1
export REPOPILOT_MODEL=your-local-model
python -m repopilot.cli propose examples/calculator examples/issue.txt --output .runs/proposal.json
# Review generated proposal and patch first.
docker pull python:3.12-alpine
python -m repopilot.cli verify examples/calculator .runs/proposal.json --output .runs/verification.json
```

For remote providers, set `REPOPILOT_BASE_URL`, `REPOPILOT_MODEL`, and `REPOPILOT_API_KEY` via environment variables. Never commit keys. **Only connect to trusted model endpoints**.

## Threat model and limits

Repository data and issue text are untrusted. Generated patches are never automatically approved. Docker provides defense in depth, not hardened hostile-code isolation. Run verification only on disposable worker machines, without host credentials or Docker socket mounts. Network is disabled within the container; image is pre-pulled. Container timeouts may require manual worker disposal if daemon cleanup fails.

No automatic repository cloning, PR creation, GitHub issue retrieval, SWE-bench result, token-saving percentage, or live model resolution rate is claimed.

This project is deliberately distinct from the existing portfolio's browser simulations. Real provider inference, Docker verification, and issue benchmarks must be demonstrated and measured before being advertised as completed features.
