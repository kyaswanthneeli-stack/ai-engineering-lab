from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from repopilot import native_runtime
from repopilot.candidate_smoke import _run_docker


class NativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        (self.root/'lib/matplotlib').mkdir(parents=True)
        (self.root/'lib/matplotlib/colors.py').write_text('value = 1\n')
        self.targets=['lib/matplotlib/colors.py']

    def test_only_explicit_supported_namespace_uses_digest_pinned_image(self):
        with patch.dict('os.environ',{'REPOPILOT_CANDIDATE_MATPLOTLIB_NATIVE':'1'}):
            self.assertTrue(native_runtime.selected(self.targets))
            self.assertFalse(native_runtime.selected(['sympy/core/basic.py']))
        with patch.dict('os.environ',{'REPOPILOT_CANDIDATE_MATPLOTLIB_NATIVE':'other/image:latest'}):
            self.assertFalse(native_runtime.selected(self.targets))
        self.assertIn('@sha256:',native_runtime.MATPLOTLIB_IMAGE)

    def test_native_prefix_checks_base_source_hash_and_workspace_origin(self):
        code=native_runtime.prefix(self.root,self.targets)
        self.assertIn(native_runtime.MATPLOTLIB_BASE,code)
        self.assertIn("'diff','--quiet'",code)
        self.assertIn('raise SystemExit(78)',code)
        self.assertIn('/workspace/lib/matplotlib/__init__.py',code)
        self.assertIn('/testbed/lib/matplotlib',code)

    def test_unsafe_paths_and_symlinked_parents_refused(self):
        with self.assertRaises(ValueError):
            native_runtime.prefix(self.root,['lib/matplotlib/../../escape.py'])
        with tempfile.TemporaryDirectory() as outside:
            (Path(outside)/'colors.py').write_text('value=1\n')
            (self.root/'lib/matplotlib/linked').symlink_to(outside,target_is_directory=True)
            with self.assertRaises(ValueError):
                native_runtime.prefix(self.root,['lib/matplotlib/linked/colors.py'])

    def test_docker_remains_restricted_and_uses_native_python_with_no_pull(self):
        seen=[]
        def run(args,**kwargs):
            seen.append(args)
            return subprocess.CompletedProcess(args,0)
        with patch.dict('os.environ',{'REPOPILOT_CANDIDATE_MATPLOTLIB_NATIVE':'1'}),patch(
                'repopilot.candidate_smoke.subprocess.run',side_effect=run):
            code,unsafe=_run_docker(self.root,'import matplotlib.colors',overlay=None,
                targets=self.targets,timeout=7)
        self.assertEqual((code,unsafe),(0,False))
        for flag in ('--network=none','--pull=never','--user=65534:65534','--read-only',
                     '--security-opt=no-new-privileges','--memory=512m','--pids-limit=64'):
            self.assertIn(flag,seen[0])
        self.assertIn(native_runtime.MATPLOTLIB_IMAGE,seen[0])
        self.assertIn(native_runtime.NATIVE_PYTHON,seen[0])

    def test_provenance_failure_is_unavailable_never_regression(self):
        diagnostics={}
        with patch.dict('os.environ',{'REPOPILOT_CANDIDATE_MATPLOTLIB_NATIVE':'1'}),patch(
                'repopilot.candidate_smoke.subprocess.run',
                return_value=subprocess.CompletedProcess([],78)):
            result=_run_docker(self.root,'import matplotlib.colors',overlay=None,
                targets=self.targets,timeout=7,diagnostics=diagnostics,phase='candidate')
        self.assertEqual(result,(None,False))
        self.assertEqual(diagnostics['candidate_failure_category'],'runtime_provenance_unavailable')
