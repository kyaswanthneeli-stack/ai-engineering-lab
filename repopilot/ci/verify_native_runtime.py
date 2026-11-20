"""Check the one approved native image, inside the existing Docker boundary."""
import argparse
from pathlib import Path
import subprocess

from repopilot.native_runtime import MATPLOTLIB_IMAGE, NATIVE_PYTHON, source_guard

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.parent.mkdir(parents=True, exist_ok=True)
script = source_guard(report=True) + (
    "import matplotlib,matplotlib._c_internal_utils,matplotlib._path,sys,json,hashlib\n"
    "from pathlib import Path\n"
    "_native=Path(matplotlib._c_internal_utils.__file__)\n"
    "print(json.dumps({'python':sys.version.split()[0],'matplotlib_source':matplotlib.__file__,"
    "'native_extension':str(_native),'native_extension_sha256':hashlib.sha256(_native.read_bytes()).hexdigest()}))\n"
)
command = [
    'docker','run','--rm','--pull=never','--network=none','--read-only',
    '--user=65534:65534','--cap-drop=ALL','--security-opt=no-new-privileges',
    '--memory=512m','--cpus=1','--pids-limit=64',
    '--tmpfs=/tmp:rw,nosuid,nodev,size=32m,mode=1777',
    '-e','MPLCONFIGDIR=/tmp/mpl-config','-e','MPLBACKEND=Agg',
    '-e','OPENBLAS_NUM_THREADS=1','-e','PYTHONDONTWRITEBYTECODE=1',
    '-w','/testbed','--entrypoint',NATIVE_PYTHON,MATPLOTLIB_IMAGE,'-c',script,
]
with args.output.open('w') as output:
    subprocess.run(command, stdout=output, timeout=60, check=True)
