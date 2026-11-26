"""Evaluate unittest output without confusing import errors with reproduced bugs.

Unittest's process exit code alone is insufficient: syntax/import errors also
exit nonzero. A valid reproduction must add tests and produce an actual FAIL.
"""
from __future__ import annotations
import re

from .sandbox import RunResult

_COUNT = re.compile(r"(?m)^Ran (\d+) tests? in ")
_FAIL = re.compile(r"(?m)^FAIL: ")
_ERROR = re.compile(r"(?m)^ERROR: ")


def test_count(output: str) -> int | None:
    matches = _COUNT.findall(output)
    return int(matches[-1]) if matches else None


def check_three_stage_evidence(baseline, before, after) -> None:
    """Raise ValueError unless a clean baseline, genuine test failure, and clean fix exist."""
    states = (baseline, before, after)
    if any(getattr(s, "timed_out", False) for s in states):
        raise ValueError("Timed-out tests cannot establish a verified fix")
    if baseline.exit_code != 0 or before.exit_code == 0 or after.exit_code != 0:
        raise ValueError("Expected passing baseline, failing reproduction and passing patched suite")
    counts = [test_count(s.output) for s in states]
    if any(n is None for n in counts):
        raise ValueError("Unittest output lacks a valid number of executed tests")
    if not (counts[1] > counts[0] and counts[2] >= counts[1]):
        raise ValueError("Reproduction did not add and retain executed tests")
    if _ERROR.search(before.output):
        raise ValueError("Import/runtime test errors do not count as a reproduced bug")
    if not _FAIL.search(before.output):
        raise ValueError("Expected a genuine unittest assertion failure, not another exit error")
    if _ERROR.search(baseline.output) or _FAIL.search(baseline.output):
        raise ValueError("Baseline output contains failed tests")
    if _ERROR.search(after.output) or _FAIL.search(after.output):
        raise ValueError("Patched test output contains failed tests")


def check_verification_report(report: dict) -> None:
    """Validate recorded unittest results before using a report as evidence."""
    if not isinstance(report, dict) or report.get("outcome") != "verified_in_sandbox":
        raise ValueError("Report does not record a verified outcome")
    results = []
    for stage in ("baseline", "before", "after"):
        entry = report.get(stage)
        if (not isinstance(entry, dict)
                or type(entry.get("exit_code")) is not int
                or not isinstance(entry.get("output"), str)
                or type(entry.get("timed_out")) is not bool):
            raise ValueError(f"Missing or invalid {stage} test result")
        results.append(RunResult(entry["exit_code"], 0, entry["output"], entry["timed_out"]))
    check_three_stage_evidence(*results)
