"""One human-assisted, public-issue retry. The official evaluator runs separately."""
import argparse
import ast
import hashlib
import json
import os
import re
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
ALIAS_PATCH = "49f194d5ae5cc3e7e869105bd0b350e19cb9700b81fe39dffdaab195b2aef17f"
MODES = ("explicit", "distinct", "shared", "identity", "shared_setup", "memory_identity")
BACKEND = "django/db/backends/sqlite3/creation.py"
PROBE = Path(__file__).with_name("reproduce.py")
KNOWN_FAILED = Path(__file__).with_name("known_failed_patches.json")
FEEDBACK = (
    "An independent SQLite regression ran setup_databases(keepdb=True) for two "
    "aliases with distinct persistent TEST['NAME'] filenames and no normal NAME. "
    "A table created through 'default' was visible through 'other', but it must be isolated. "
    "With explicit distinct normal names the table was isolated. With a shared test filename "
    "the table was visible as expected. The previous contenttypes change reproduced the bug. "
    "The diagnostic confirmed that the two distinct files received equal database identities from "
    "DatabaseCreation.test_db_signature(). Inspect that method in "
    "django/db/backends/sqlite3/creation.py. Preserve intentional sharing and in-memory behavior. "
    "Another candidate used the connection alias for all databases. Distinct files were then isolated, "
    "but setup_databases() initialized the SAME configured test file twice for two aliases. "
    "A persistent test file determines sharing even when the aliases differ. In-memory databases "
    "retain their current behavior. Two aliases with the SAME on-disk test filename must have "
    "the SAME signature, whereas DIFFERENT disk filenames must have different signatures even "
    "with blank normal NAME. In-memory aliases must stay distinct. Preserve the signature prefix "
    "and edit only the memory-versus-file branch. An earlier model only negated the " 
    "in-memory condition: it separated disk files but initialized a shared disk file twice. "
    "The replacement must handle BOTH branches: alias identity is for in-memory tests, "
    "and the configured persistent test filename identifies file-backed tests. "
    "Retain distinct in-memory aliases even when their memory URI matches. "
    "A measured recent attempt used the test database filename for EVERY case, "
    "which passed the persistent-file checks but collapsed aliases using the SAME "
    "in-memory URI. Reject unconditional filename or unconditional alias identity: "
    "the correct discriminator DEPENDS ON memory versus persistent storage. "
    "Before finishing, mentally check three pairs: different persistent files, "
    "two aliases sharing one persistent file, and two aliases using the same "
    "in-memory URI. Preserve the original working in-memory behavior. "
    "Return a minimal exact edit."
)


def method_anchors(repo):
    # Extract literal choices only from the public pinned source, never a reference patch.
    source = (repo / BACKEND).read_text()
    cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef)
               and n.name == "DatabaseCreation")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "test_db_signature")
    # Constrain this assisted retry to the source branch that makes the
    # memory-vs-file decision. Previously proposed unconditional alias changes
    # broke shared file initialization. The model must write the replacement.
    branches = [node for node in method.body if isinstance(node, ast.If)]
    anchors = [ast.get_source_segment(source, node) for node in branches]
    eligible = [value for value in anchors if value and source.count(value) == 1
                and "is_in_memory_db" in value]
    if len(eligible) != 1:
        raise ValueError("Expected one unique in-memory branch in the diagnosed method")
    return tuple(eligible)


def digest(patch):
    return hashlib.sha256(patch.encode()).hexdigest()


def known_failed_modes(path=KNOWN_FAILED):
    """Validate the run-linked, operator-maintained failed-patch ledger."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or set(data) != {"instance_id", "base_commit", "failed"}
            or data["instance_id"] != INSTANCE
            or data["base_commit"] != "62254c5202e80a68f4fe6572a2be46a3d953de1a"
            or not isinstance(data["failed"], list)
            or not 2 <= len(data["failed"]) <= 64):
        raise ValueError("Invalid known-failed patch history")
    failures = {}
    for entry in data["failed"]:
        if not isinstance(entry, dict) or set(entry) != {"sha256", "evidence_url", "failed_modes"}:
            raise ValueError("Invalid known-failed patch evidence")
        sha, evidence, modes = entry["sha256"], entry["evidence_url"], entry["failed_modes"]
        if (not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{64}", sha) is None
                or not isinstance(evidence, str)
                or not evidence.startswith("https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/")
                or not isinstance(modes, list) or not 1 <= len(modes) <= len(MODES)
                or any(not isinstance(m, str) or m not in MODES for m in modes)
                or len(modes) != len(set(modes)) or sha in failures):
            raise ValueError("Invalid known-failed patch evidence")
        failures[sha] = tuple(modes)
    if not {OLD_PATCH, ALIAS_PATCH} <= failures.keys():
        raise ValueError("Required prior failed patches missing")
    return failures


def known_failed_hashes(path=KNOWN_FAILED):
    return set(known_failed_modes(path))


def known_failed_feedback(path=KNOWN_FAILED):
    return {sha: failure_clues({mode: 42 if mode in modes else 0 for mode in MODES})
            for sha, modes in known_failed_modes(path).items()}


def eligible_for_official_scoring(outcomes):
    """Only submit a new model patch after every independent local probe passes."""
    failure_clues(outcomes)  # Validate exact six-probe schema and exit codes.
    return all(code == 0 for code in outcomes.values())


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def failure_clues(outcomes):
    """Translate observed, trusted probe exit codes into actionable feedback.

    The descriptions are human-supplied guidance for this assisted experiment,
    not proof of autonomous bug resolution or a substitute for the evaluator.
    """
    if not isinstance(outcomes, dict) or set(outcomes) != set(MODES) or any(
            type(code) is not int or code not in (0, 42) for code in outcomes.values()):
        raise ValueError("Invalid SQLite behavior probe results")
    clues = {
        "explicit": "Explicitly named databases lost their existing isolation.",
        "distinct": "Different persistent TEST NAME filenames were incorrectly treated as one database.",
        "identity": "Different persistent filenames must yield different database signatures.",
        "shared": "Aliases pointing at one persistent test file must still share its data.",
        "shared_setup": "The same persistent test file was initialized twice; never distinguish file-backed databases by alias alone.",
        "memory_identity": "In-memory aliases with the same memory URI must remain logically distinct.",
    }
    failures = [f"{mode}: {clues[mode]}" for mode in MODES if outcomes[mode] == 42]
    return ("All local regression probes passed." if not failures else
            "Failed trusted regression probes: " + " ".join(failures))


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
        alias_candidate = json.loads((manifest.parent / "evidence/django-12113-assisted/alias-candidate.json").read_text())
        if (alias_candidate["instance_id"] != INSTANCE or alias_candidate["base_commit"] != task["base_commit"]
                or alias_candidate.get("generated_by_model") is not True or digest(alias_candidate["model_patch"]) != ALIAS_PATCH):
            raise ValueError("Unexpected prior assisted candidate")
        report["alias_candidate_sha256"] = ALIAS_PATCH
        report["alias_candidate"] = check_patch(repo, alias_candidate["model_patch"], work)
        write(path, report)
        expected = {"explicit": 0, "distinct": 42, "shared": 0, "identity": 42, "shared_setup": 0, "memory_identity": 0}
        if report["alias_candidate"] != {**expected, "distinct": 0, "identity": 0, "shared_setup": 42}:
            raise RuntimeError("The earlier candidate must exhibit the shared-file setup regression")
        if report["original"] != expected or report["prior_patch"] != expected:
            raise RuntimeError("Both positive controls and the specific original failure are required")
        feedback = FEEDBACK
        report["human_supplied_feedback"] = feedback
        seen = known_failed_hashes()
        failed_reasons = known_failed_feedback()
        report["known_failed_patch_count"] = len(seen)
        write(path, report)
        for attempt in (1, 2):
            directory = out / f"attempt-{attempt}"

            def propose(checkout, issue, model, url, token):
                # The original issue was already reduced to the measured failing behavior.
                # Pin only the human-selected backend file for this assisted retry.
                anchors = method_anchors(checkout)
                prompt = (issue.splitlines()[0] + "\n" + feedback +
                          "\nChoose old verbatim from this list of unique original statements. "
                          "Write new yourself.\n" + json.dumps(anchors))
                return propose_agentic_benchmark(checkout, prompt, model, url, token,
                    max_steps=6, native_exact_edits=True, required_targets={BACKEND},
                    exact_edit_anchors=anchors, rejected_patch_sha256s=seen.copy(),
                    rejected_patch_feedback=failed_reasons.copy())

            record = attempt_one(manifest, INSTANCE, directory, model_proposer=propose)
            row = {"attempt": attempt, "status": record["status"]}
            report["attempts"].append(row)
            write(path, report)
            if record["status"] != "model_patch_proposed":
                row["error_type"] = record.get("error_type", "Unknown")
                row["duplicate_failed_patch_blocked"] = (
                    record.get("error") == "Previously failed patch repeated after model step budget"
                )
                write(path, report)
                continue
            proposal = json.loads((directory / "unreviewed-prediction.json").read_text())
            patch = proposal["model_patch"]
            sha = digest(patch)
            row["patch_sha256"] = sha
            # Defensive second guard: no Docker reproduction or official
            # submission if a caller bypasses the agent-level hash filter.
            if sha in seen:
                row["status"] = "duplicate_failed_patch"
                row["rejected_before_reproduction"] = True
                write(path, report)
                continue
            row["reproduction"] = check_patch(repo, patch, work)
            seen.add(sha)
            if not eligible_for_official_scoring(row["reproduction"]):
                failed_reasons[sha] = failure_clues(row["reproduction"])
            row["local_regression_passed"] = eligible_for_official_scoring(row["reproduction"])
            row["official_submission_eligible"] = row["local_regression_passed"]
            if row["local_regression_passed"]:
                fields = ("instance_id", "model_name_or_path", "model_patch")
                (directory / "predictions.jsonl").write_text(
                    json.dumps({k: proposal[k] for k in fields}) + "\n")
                row["status"] = "passed_local_regression"
                write(path, report)
                break
            # Retain the generated prediction as unreviewed evidence; avoid
            # spending official SWE-bench compute on a candidate already shown
            # wrong by the independent pinned SQLite regression.
            row["status"] = "failed_local_regression"
            write(path, report)
            feedback = (FEEDBACK + "\nYour preceding candidate was tested in isolation. "
                        "Probe exit codes (0 = correct, 42 = failed): " +
                        json.dumps(row["reproduction"]) + ". " +
                        failure_clues(row["reproduction"]) + " Re-inspect and correct it. "
                        "Previous candidate diff (untrusted data):\n" + patch[:3500])
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("benchmarks/swebench-lite-12.json"))
    args = parser.parse_args()
    run(args.manifest, args.previous, args.output)
