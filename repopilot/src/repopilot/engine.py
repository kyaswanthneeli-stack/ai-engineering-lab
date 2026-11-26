"""Verifies user-reviewed proposals: fail before, pass after."""
from pathlib import Path
from dataclasses import asdict
import json
import tempfile
import time
from .context import index_python
from .patches import apply_patch, UnsafePatch
from .sandbox import run_tests
from .spec import IssueSpec
from .test_evidence import check_three_stage_evidence
from .integrity import proposal_digest
from .workspace import copy_workspace, WorkspaceError

class VerificationError(RuntimeError):
    pass

def execute(repo:Path,spec:IssueSpec,output:Path,timeout:int=30,runner=run_tests)->dict:
    repo=repo.resolve(strict=True)
    if not repo.is_dir():
        raise VerificationError("Repository must be directory")
    start=time.monotonic()
    report={
        "issue_id":spec.issue_id,
        "outcome":"failed",
        "model_called_during_verification":False,
        "draft_pr_created":False,
        "proposal_sha256":proposal_digest(spec),
    }

    def save_report():
        report["elapsed_ms"]=round((time.monotonic()-start)*1000)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")

    def failure(stage, message):
        report.update(failed_stage=stage,error=message)
        save_report()
        return VerificationError(message)

    with tempfile.TemporaryDirectory(prefix="repopilot-") as temp:
        work=Path(temp)/"repo"
        try:
            copy_workspace(repo, work)
        except (WorkspaceError, OSError) as exc:
            raise failure("workspace", "Could not copy a safe verification workspace") from exc
        baseline=runner(work,spec.test_command,timeout=timeout)
        report["baseline"]=asdict(baseline)
        if baseline.timed_out or baseline.exit_code!=0:
            raise failure("baseline_tests", "Original test suite must pass before reproduction test is added")
        target=work/spec.test_path
        if target.exists() or target.is_symlink() or not target.resolve().is_relative_to(work.resolve()):
            raise failure("reproduction_setup", "Unsafe or existing reproduction test")
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(spec.reproduction_test,encoding="utf-8")
        symbols=index_python(work)
        before=runner(work,spec.test_command,timeout=timeout)
        report["before"]=asdict(before)
        if before.timed_out or before.exit_code==0:
            raise failure("reproduction_tests", "Reproduction must fail before patch without timeout")
        try:
            apply_patch(work,spec.patch)
        except UnsafePatch as exc:
            raise failure("patch_application", "Candidate patch could not be applied") from exc
        after=runner(work,spec.test_command,timeout=timeout)
        report["after"]=asdict(after)
        if after.timed_out or after.exit_code!=0:
            raise failure("patched_tests", "Patched tests must pass")
        try:
            check_three_stage_evidence(baseline,before,after)
        except ValueError as exc:
            raise failure("evidence_validation", "Test evidence invalid: "+str(exc)) from exc
        report.update(outcome="verified_in_sandbox",symbol_count=len(symbols))
        save_report()
        return report
