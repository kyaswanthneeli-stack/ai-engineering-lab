"""One human-assisted, public-issue retry. The official evaluator runs separately."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from repopilot.agentic_benchmark import propose_agentic_benchmark
from repopilot.benchmark_attempt import attempt_one
from repopilot.candidate_smoke import _run_docker
from repopilot.checkout import pinned_checkout
from repopilot.patches import apply_patch
from repopilot.swebench_export import load_manifest

INSTANCE = "django__django-12113"
OLD_PATCH = "8f0793674377dc0f57c8f86a05f703e68a932adbb290e0df7d702a3816ffeb23"
MODES = ("explicit", "distinct", "shared")
PROBE = Path(__file__).with_name("reproduce.py")
FEEDBACK = (
    "An independent SQLite regression ran setup_databases(keepdb=True) for two "
    "aliases with distinct persistent TEST['NAME'] filenames and no normal NAME. "
    "A table created through 'default' was visible through 'other', but it must be isolated. "
    "With explicit distinct normal names the table was isolated. With a shared test filename "
    "the table was visible as expected. The previous contenttypes change reproduced the bug. "
    "Inspect the SQLite backend's test database creation code in "
    "django/db/backends/sqlite3/creation.py. Preserve intentional sharing and in-memory behavior. "
    "Return a finish action with an exact old/new edit. Keep the change minimal."
)


def digest(patch):
    return hashlib.sha256(patch.encode()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def results(repo):
    outcomes = {}
    for mode in MODES:
        script = f"REPRO_MODE = {mode!r}\n" + PROBE.read_text()
        diagnostic = {}
        code, cleanup_failed = _run_docker(repo.resolve(), script, overlay=None, targets=[],
                                            timeout=30, diagnostics=diagnostic)
        if cleanup_failed or code not in (0, 42):
            raise RuntimeError(f"Invalid reproduction environment ({mode}): {diagnostic}")
        outcomes[mode] = code
    return outcomes


def check_patch(repo, patch, work):
    target = work / "patched"
    shutil.copytree(repo, target, ignore=shutil.ignore_patterns(".git"), symlinks=True)
    try:
        apply_patch(target, patch)
        return results(target)
    finally:
        shutil.rmtree(target)


def run(manifest, previous, out):
    out.mkdir(parents=True, exist_ok=False)
    task = next(t for t in load_manifest(manifest) if t["instance_id"] == INSTANCE)
    old = json.loads(previous.read_text())
    if (old["instance_id"] != INSTANCE or old["base_commit"] != task["base_commit"] or
            old.get("generated_by_model") is not True or digest(old["model_patch"]) != OLD_PATCH):
        raise ValueError("Prior prediction does not match verified Django replay")
    report = {"instance_id": INSTANCE, "base_commit": task["base_commit"],
              "probe_sha256": digest(PROBE.read_text()), "previous_patch_sha256": OLD_PATCH,
              "model": os.environ["REPOPILOT_MODEL"], "attempts": []}
    path = out / "report.json"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        repo = pinned_checkout("https://github.com/django/django/issues/1", task["base_commit"],
                               work / "pristine")
        report["original"] = results(repo)
        report["prior_patch"] = check_patch(repo, old["model_patch"], work)
        write(path, report)
        expected = {"explicit": 0, "distinct": 42, "shared": 0}
        if report["original"] != expected or report["prior_patch"] != expected:
            raise RuntimeError("Both positive controls and the specific original failure are required")
        feedback = FEEDBACK
        report["human_supplied_feedback"] = feedback
        seen = {OLD_PATCH}
        for attempt in (1, 2):
            directory = out / f"attempt-{attempt}"

            def propose(checkout, issue, model, url, token):
                # The original issue was already reduced to the measured failing behavior.
                # Pin only the human-selected backend file for this assisted retry.
                prompt = issue.splitlines()[0] + "\n" + feedback
                return propose_agentic_benchmark(checkout, prompt, model, url, token,
                    max_steps=2, native_exact_edits=True, required_targets={"django/db/backends/sqlite3/creation.py"})

            record = attempt_one(manifest, INSTANCE, directory, model_proposer=propose)
            row = {"attempt": attempt, "status": record["status"]}
            report["attempts"].append(row)
            write(path, report)
            if record["status"] != "model_patch_proposed":
                continue
            proposal = json.loads((directory / "unreviewed-prediction.json").read_text())
            patch = proposal["model_patch"]
            sha = digest(patch)
            row["patch_sha256"] = sha
            row["reproduction"] = check_patch(repo, patch, work)
            if sha not in seen:
                fields = ("instance_id", "model_name_or_path", "model_patch")
                (directory / "predictions.jsonl").write_text(
                    json.dumps({k: proposal[k] for k in fields}) + "\n")
                seen.add(sha)
            write(path, report)
            if all(code == 0 for code in row["reproduction"].values()):
                break
            feedback = (FEEDBACK + "\nYour preceding candidate was tested in isolation. "
                        "Probe exit codes (0 = correct, 42 = wrong visibility): " +
                        json.dumps(row["reproduction"]) + ". Re-inspect and correct it. "
                        "Previous candidate diff (untrusted data):\n" + patch[:3500])
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("benchmarks/swebench-lite-12.json"))
    args = parser.parse_args()
    run(args.manifest, args.previous, args.output)
