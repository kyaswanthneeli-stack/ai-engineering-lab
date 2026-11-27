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
