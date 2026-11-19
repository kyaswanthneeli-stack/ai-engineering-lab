"""Explainable static review of a model-proposed patch and regression test.

Heuristics aren't a security scanner. They surface high-risk operations before
the draft PR approval gate. They never execute model-authored code.
"""
from __future__ import annotations
import ast
import re
from dataclasses import dataclass
from .spec import IssueSpec
from .patches import validate_patch

@dataclass(frozen=True)
class Finding:
    severity:str
    code:str
    message:str

DANGEROUS_IMPORTS={"subprocess","socket","ctypes","pickle"}
DANGEROUS_CALLS={"eval","exec","compile","__import__"}
SECRET=re.compile(r"(?:password|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"][^'\"]{8,}",re.IGNORECASE)

def review_proposal(spec:IssueSpec)->dict:
    validate_patch(spec.patch)
    findings=[]
    try:
        tree=ast.parse(spec.reproduction_test)
    except SyntaxError:
        findings.append(Finding("blocker","invalid_test_syntax","Reproduction test must parse as Python"))
        tree=None
    if tree:
        tests=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith("test_")]
        if not tests:
            findings.append(Finding("blocker","missing_test_method","Reproduction test contains no test_ method"))
        imported=set()
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):
                imported.update(alias.name.split(".")[0] for alias in n.names)
            elif isinstance(n,ast.ImportFrom) and n.module:
                imported.add(n.module.split(".")[0])
            elif isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in DANGEROUS_CALLS:
                findings.append(Finding("blocker","dangerous_test_call",f"Reproduction test uses {n.func.id}()"))
        for module in sorted(imported & DANGEROUS_IMPORTS):
            findings.append(Finding("blocker","dangerous_test_import",f"Reproduction test imports {module}"))
    added=[line[1:] for line in spec.patch.splitlines()
           if line.startswith("+") and not line.startswith("+++")]
    added_text="\n".join(added)
    for api in ("os.system(","subprocess.","socket.","eval(","exec("):
        if api in added_text:
            findings.append(Finding("warning","risky_patch_operation",f"Added code contains {api}"))
    if SECRET.search(added_text):
        findings.append(Finding("blocker","possible_secret","Added code resembles a credential assignment"))
    blocked=any(f.severity=="blocker" for f in findings)
    return {"status":"blocked" if blocked else "review_required",
            "blockers":sum(f.severity=="blocker" for f in findings),
            "warnings":sum(f.severity=="warning" for f in findings),
            "findings":[f.__dict__ for f in findings],
            "notice":"Static checks only; this is not a security guarantee or a human code review."}
