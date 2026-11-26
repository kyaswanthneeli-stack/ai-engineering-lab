# Operator validation on a Mac and a disposable GitHub repository

The existing [hosted one-case experiment](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/45904411806) ran Docker and Ollama on a standard GitHub Actions runner. A laptop provides another way to collect inference data if you can sign in and start the local applications.

## Prepare a local worker

On Apple silicon, install the Apple silicon build of [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/) and the [macOS Ollama app](https://docs.ollama.com/macos). Start both applications. Use the free personal-use option where applicable. Install Git, Python 3.11 or newer, and the [GitHub CLI](https://cli.github.com/) if they are missing. Then open Terminal from a fresh checkout of the engineering lab:

```bash
git clone https://github.com/kyaswanthneeli-stack/ai-engineering-lab.git
cd ai-engineering-lab/repopilot
open -a Docker
open -a Ollama
docker info --format '{{.ServerVersion}}'
docker pull python:3.12-alpine
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e . 'datasets>=3,<5'
ollama pull qwen2.5-coder:3b

export REPOPILOT_MODEL=qwen2.5-coder:3b
export REPOPILOT_BASE_URL=http://127.0.0.1:11434/v1
export REPOPILOT_OLLAMA_NATIVE=1
export REPOPILOT_PROVIDER_TIMEOUT_SECONDS=120
export REPOPILOT_AGENT_BUDGET_SECONDS=420
export REPOPILOT_MAX_TOKENS=1024
python -m repopilot.cli doctor --live
```

A successful doctor run reports `ready_for_verified_workflow: true`. To run the diagnostic case with no manually supplied source hints:

```bash
docker build -t repopilot-candidate-deps:py310 -f ci/Dockerfile.candidate-smoke ci
export REPOPILOT_CANDIDATE_SMOKE=1
export REPOPILOT_CANDIDATE_SMOKE_BOOTSTRAP=1
export REPOPILOT_CANDIDATE_SMOKE_IMAGE=repopilot-candidate-deps:py310
python -m repopilot.benchmark_attempt django__django-12113 \
  --agentic --max-steps 12 --output ".runs/mac-django-$(date +%s)"
```

Keep `attempt.json` and any generated prediction together. Official scoring uses the separate SWE-bench evaluator. The networkless verification containers and optional dependency image run on the trusted worker. The Ollama API stays bound to localhost.

## Test real draft publication in a private fixture repository

Run from the same `repopilot/` directory after Docker and the Python environment are ready. Sign into GitHub on your Mac. Use a GitHub account that may create a private repository for this test. The following commands create a uniquely named repository containing only the calculator fixture and one issues record. They leave the published PR as a draft.

```bash
gh auth login --web --git-protocol https
gh auth setup-git
operator="$(gh api user --jq .login)"
operator_id="$(gh api user --jq .id)"
remote="$operator/repopilot-publish-smoke-$(date -u +%Y%m%d-%H%M%S)"
smoke="$(mktemp -d)"
mkdir "$smoke/repo"
cp -R fixtures/calculator-buggy/. "$smoke/repo/"
git -C "$smoke/repo" init -b main
git -C "$smoke/repo" add calculator.py tests
git -C "$smoke/repo" -c user.name="$operator" \
  -c user.email="$operator_id+$operator@users.noreply.github.com" \
  commit -m 'Seed the calculator publication fixture'
gh repo create "$remote" --private --source "$smoke/repo" --remote origin --push
issue_url="$(gh issue create --repo "$remote" --title 'Division by zero should raise' \
  --body 'Disposable RepoPilot publication test using the bundled calculator fixture.')"
python - "$remote" "${issue_url##*/}" "$smoke/proposal.json" <<'PY'
import json
import sys
from pathlib import Path

remote, issue_number, destination = sys.argv[1:]
spec = json.loads(Path("examples/issue.json").read_text())
spec["issue_id"] = f"{remote}#{issue_number}"
Path(destination).write_text(json.dumps(spec, indent=2) + "\n")
PY
python -m repopilot.cli verify "$smoke/repo" "$smoke/proposal.json" --output "$smoke/verification.json"
```

Read `"$smoke/proposal.json"` and `"$smoke/verification.json"`. Confirm the baseline, reproduction, and patched exit codes are 0, 1, and 0. After reviewing the exact patch and approving its submission to the fixture repository, run:

```bash
GITHUB_TOKEN="$(gh auth token)" python -m repopilot.cli draft-pr \
  "$smoke/repo" "$smoke/proposal.json" "$smoke/verification.json" \
  --remote "$remote" --approve I_APPROVE_DRAFT_PR > "$smoke/publication.json"
pr_number="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["number"])' "$smoke/publication.json")"
gh pr view "$pr_number" --repo "$remote" --json url,isDraft,baseRefName,headRefName
gh pr diff "$pr_number" --repo "$remote" --name-only
```

The reported PR should have `isDraft: true`, base `main`, and exactly `calculator.py` and `tests/test_reproduction.py` in the diff. Keep the PR URL and the verification report as evidence. Never paste the GitHub token into the terminal history or into a report.
