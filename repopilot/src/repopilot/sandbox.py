"""Docker-based, network-restricted test subprocess."""
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from threading import Thread
import time
import uuid

@dataclass(frozen=True)
class RunResult:
    exit_code:int
    elapsed_ms:int
    output:str
    timed_out:bool=False

def _run_with_output_tail(args: list[str], timeout: int) -> tuple[int, str]:
    """Drain both streams while retaining at most 12,000 bytes of output."""
    read_fd, write_fd = os.pipe()
    tail = bytearray()

    def read_output():
        with os.fdopen(read_fd, "rb") as stream:
            for chunk in iter(lambda: stream.read1(8192), b""):
                tail.extend(chunk)
                del tail[:-12000]

    reader = Thread(target=read_output, daemon=True)
    reader.start()
    try:
        with os.fdopen(write_fd, "wb") as stream:
            completed = subprocess.run(
                args, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout, check=False
            )
    finally:
        reader.join(timeout=1)
    if reader.is_alive():
        raise RuntimeError("Docker output stream did not close")
    return completed.returncode, tail.decode("utf-8", errors="replace")


def run_tests(repo:Path,command:tuple[str,...],timeout:int=30)->RunResult:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker unavailable; verification not run")
    if not 1<=timeout<=120:
        raise ValueError("Timeout out of range")
    if command!=("python","-m","unittest","discover","-s","tests","-v"):
        raise ValueError("Unapproved command")
    container="repopilot-"+uuid.uuid4().hex[:16]
    args=["docker","run","--name",container,"--rm","--log-driver=none","--pull=never","--network=none","--cap-drop=ALL","--security-opt=no-new-privileges","--pids-limit=64","--memory=512m","--cpus=1","--read-only","--tmpfs=/tmp:rw,nosuid,nodev,size=32m,mode=1777","--user=65534:65534","-e","PYTHONDONTWRITEBYTECODE=1","-e","PYTHONPATH=/workspace","-v",f"{repo.resolve()}:/workspace:ro","-w","/workspace","python:3.12-alpine",*command]
    start=time.monotonic()
    try:
        code, output=_run_with_output_tail(args, timeout)
        return RunResult(code,round((time.monotonic()-start)*1000),output)
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
