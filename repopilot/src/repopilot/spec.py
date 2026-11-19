"""Strict JSON proposal contract."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass(frozen=True)
class IssueSpec:
    issue_id: str
    summary: str
    test_path: str
    reproduction_test: str
    patch: str
    test_command: tuple[str,...]

    @classmethod
    def from_dict(cls, raw: dict):
        required = {"issue_id","summary","test_path","reproduction_test","patch","test_command"}
        if not isinstance(raw,dict) or set(raw) != required:
            raise ValueError("Invalid proposal keys")
        for key in required-{"test_command"}:
            if not isinstance(raw[key],str) or not raw[key] or len(raw[key]) > 100_000:
                raise ValueError(f"Invalid proposal field: {key}")
        if raw["test_command"] != ["python","-m","unittest","discover","-s","tests","-v"]:
            raise ValueError("Only fixed unittest discovery is allowed")
        p = Path(raw["test_path"])
        if p.is_absolute() or ".." in p.parts or not raw["test_path"].startswith("tests/") or p.suffix != ".py" or "\\" in raw["test_path"]:
            raise ValueError("Unsafe test path")
        return cls(**{**raw,"test_command":tuple(raw["test_command"])})
    @classmethod
    def from_json(cls,path:Path):
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
