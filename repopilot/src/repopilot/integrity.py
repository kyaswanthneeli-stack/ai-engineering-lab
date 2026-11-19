"""Deterministic identification of the exact proposal that was verified.

A SHA-256 digest catches accidental mismatches between proposed code and
verification reports. It does NOT authenticate a report or replace human review.
"""
from __future__ import annotations
from hashlib import sha256
import json
from .spec import IssueSpec


def proposal_digest(spec: IssueSpec) -> str:
    value = {
        "issue_id": spec.issue_id,
        "patch": spec.patch,
        "reproduction_test": spec.reproduction_test,
        "test_command": list(spec.test_command),
        "test_path": spec.test_path,
    }
    data = json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
    return sha256(data).hexdigest()
