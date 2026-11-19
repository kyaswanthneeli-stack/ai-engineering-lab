"""Docker-based, network-restricted test subprocess."""
from dataclasses import dataclass,asdict
from pathlib import Path
import shutil
import subprocess
import time
import uuid

@dataclass(frozen=True)
class RunResult:
    exit_code:int
    elapsed_ms:int
    output:str
    timed_out:bool=False

def run_tests(repo:Path,command:tuple[str,...],timeout:int=30)->RunResult:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker unavailable; verification not run")
    if not 1<=timeout<=120:
        raise ValueError("Timeout out of range")
    if command!=("python","-m","unittest","discover","-s","tests","-v"):
        raise ValueError("Unapproved command")
    container="repopilot-"+uuid.uuid4().hex[:16]
    args=["docker","run","--name",container,"--rm","--pull=never","--network=none","--cap-drop=ALL","--security-opt=no-new-privileges","--pids-limit=64","--memory=512m","--cpus=1","--read-only","--tmpfs=/tmp:rw,nosuid,nodev,size=32m,mode=1777","--user=65534:65534","-e","PYTHONDONTWRITEBYTECODE=1","-e","PYTHONPATH=/workspace","-v",f"{repo.resolve()}:/workspace:ro","-w","/workspace","python:3.12-alpine",*command]
    start=time.monotonic()
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout,check=False)
        return RunResult(p.returncode,round((time.monotonic()-start)*1000),(p.stdout+p.stderr)[-12000:])
    except subprocess.TimeoutExpired:
        try:
            cleanup=subprocess.run(["docker","rm","-f",container],timeout=8,capture_output=True,check=False)
            if cleanup.returncode==0:
                message="Timed out; Docker reported forced container removal"
            else:
                message="Timed out; Docker cleanup failed, discard worker"
        except (OSError,subprocess.TimeoutExpired):
            message="Timed out; cleanup unconfirmed, discard worker"
        return RunResult(124,round((time.monotonic()-start)*1000),message,True)
