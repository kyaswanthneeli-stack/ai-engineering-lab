---
title: RepoPilot Cloud Runner
emoji: 🧪
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# RepoPilot Cloud Runner

This web interface shows a supervised repair of RepoPilot's seeded calculator
issue. GitHub Actions runs Qwen2.5-Coder 3B with local Ollama and verifies the
proposed repair in restricted Docker. The Space displays the measured
outcome and links to the run. Visitors can view the interface. Starting a
repair requires an operator token.

## Configuration

Set the following in Hugging Face **Settings → Variables and secrets**:

- `GITHUB_TOKEN` as a secret. Use a fine-grained token restricted to
  `kyaswanthneeli-stack/ai-engineering-lab` with Actions write access.
- `REPOPILOT_ACCESS_TOKEN` as a secret. Choose a unique random value and keep
  it in the operator's password manager. Repairs are disabled without it.

Use CPU Basic if the account offers it at no charge. The Space uses no paid
inference endpoint. The daily quota is local to the instance's filesystem and
can reset when the Space is restarted or rebuilt.

## Build and evidence

From `repopilot/` in the GitHub repository:

```bash
docker build -t repopilot-space -f hf_space/Dockerfile .
docker run --rm -p 127.0.0.1:7860:7860 repopilot-space
```

A healthy HTTP endpoint proves the app started. A verified repair requires
a submitted job to report baseline pass, expected failure before the patch,
and pass after the patch. This calculator test is outside the SWE-bench
cohort. The last comparable official score is 1/12.

For GitHub deployment, set repository variable `REPOPILOT_HF_SPACE_ID` to
`OWNER/repopilot-cloud` and repository secret `REPOPILOT_HF_TOKEN` to a token
with write access only to that Space. Run **Deploy RepoPilot to Hugging Face**
from GitHub Actions on `main`. The workflow uploads to an existing Space on
CPU Basic. Then open the app and submit the calculator issue using the operator
token. Retain the resulting run link before publishing a stable release.

## Free Docker fallback on Render

The repository's root `render.yaml` declares a free Web Service using the same
Dockerfile and GitHub Actions verifier. Connect this repository to Render and
apply the blueprint with the Free plan selected. Supply a fine-grained GitHub
token restricted to this repository with Actions write access as the service's
`GITHUB_TOKEN`. Render generates the separate `REPOPILOT_ACCESS_TOKEN`.
Keep both credentials in the host's secret settings.

The welcome page and archived evidence are public. Operators start calculator
repairs using the access token. The free instance can sleep after inactivity
and lose in-memory jobs on a restart. GitHub Actions retains each completed
repair artifact. No worker runs on the operator's laptop.

## Optional Gemini verification

The hosted calculator workflow has a manual `gemini` mode for
`gemini-3.1-flash-lite`. Set repository secret
`REPOPILOT_GEMINI_FREE_TIER_KEY` using a Google AI Studio project with billing
disabled. The workflow checks for the secret before making any request.
It uses the same fixture and Docker verification. Requests launched from the
web UI use Qwen2.5-Coder 3B on GitHub Actions by default.
