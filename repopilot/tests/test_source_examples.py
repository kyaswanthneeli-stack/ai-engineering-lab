import difflib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from repopilot.candidate_smoke import _reproducer, smoke_candidate
from repopilot.source_examples import select_source_examples, runner_script

SOURCE = ('def price(x):\n'
          '    """Compute a price.\n\n'
          '    >>> price(1)\n'
          '    2\n'
          '    """\n'
          '    return x + 1\n')


class SourceExampleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root/'pricing.py').write_text(SOURCE)

    def test_original_examples_frozen_even_when_candidate_rewrites_expectation(self):
        after = SOURCE.replace('    2\n', '    0\n').replace('return x + 1', 'return x - 1')
        proposal = 'diff --git a/pricing.py b/pricing.py\n' + ''.join(difflib.unified_diff(
            SOURCE.splitlines(True), after.splitlines(True), fromfile='a/pricing.py', tofile='b/pricing.py'))
        with patch.dict('os.environ', {'REPOPILOT_CANDIDATE_SOURCE_EXAMPLES':'1'}), patch(
                'repopilot.candidate_smoke.shutil.which', return_value='docker'), patch(
                'repopilot.candidate_smoke._run_docker', side_effect=[(0,False),(1,False)]) as run:
            report = smoke_candidate(self.root, proposal, 'Preserve price behavior')
        self.assertEqual(report['status'], 'regression')
        self.assertEqual(report['probe'], 'source_doctest')
        self.assertEqual(run.call_args_list[0].args[1],run.call_args_list[1].args[1])
        self.assertIn(repr(select_source_examples(self.root,['pricing.py'])['text']),run.call_args_list[1].args[1])
        self.assertEqual((self.root/'pricing.py').read_text(),SOURCE)
        self.assertEqual(report['source_examples']['example_count'],1)
        self.assertNotIn('text',report['source_examples'])

    def test_skipped_import_only_and_excessive_examples_are_unavailable(self):
        examples = [
            '>>> price(1) # doctest: +SKIP\n2',
            '>>> import sys',
            '\n'.join('>>> price(1)\n2' for _ in range(9)),
        ]
        for doc in examples:
            with self.subTest(doc=doc):
                (self.root/'pricing.py').write_text('"""'+doc+'"""\n')
                self.assertIsNone(select_source_examples(self.root,['pricing.py']))

    def test_syntax_errors_and_symlinks_never_execute_or_escape(self):
        (self.root/'broken.py').write_text('def broken(:\n')
        self.assertIsNone(select_source_examples(self.root,['broken.py']))
        with tempfile.TemporaryDirectory() as outside:
            (Path(outside)/'leak.py').write_text(SOURCE)
            (self.root/'linked').symlink_to(outside,target_is_directory=True)
            self.assertIsNone(select_source_examples(self.root,['linked/leak.py']))

    def test_parse_does_not_execute_top_level_repository_code(self):
        sentinel=self.root/'executed'
        (self.root/'pricing.py').write_text(f'open({str(sentinel)!r}, "w").write("unsafe")\n'+SOURCE)
        selection=select_source_examples(self.root,['pricing.py'])
        self.assertIsNotNone(selection)
        runner_script(selection)
        self.assertFalse(sentinel.exists())

    def test_feature_is_opt_in_and_public_issue_example_keeps_priority(self):
        with patch.dict('os.environ',{'REPOPILOT_CANDIDATE_SOURCE_EXAMPLES':'0'}):
            self.assertEqual(_reproducer('', ['pricing.py'],root=self.root)[1],'module_import')
        with patch.dict('os.environ',{'REPOPILOT_CANDIDATE_SOURCE_EXAMPLES':'1'}):
            self.assertEqual(_reproducer('```python\nfrom pricing import price\nassert price(1)==2\n```',
                                         ['pricing.py'],root=self.root)[1],'issue_python_example')

    def test_failed_behavior_baseline_falls_back_without_false_regression(self):
        proposal='diff --git a/pricing.py b/pricing.py\n'+''.join(difflib.unified_diff(
            SOURCE.splitlines(True),SOURCE.replace('x + 1','x + 2').splitlines(True),
            fromfile='a/pricing.py',tofile='b/pricing.py'))
        with patch.dict('os.environ',{'REPOPILOT_CANDIDATE_SOURCE_EXAMPLES':'1'}), patch(
                'repopilot.candidate_smoke.shutil.which',return_value='docker'), patch(
                'repopilot.candidate_smoke._run_docker',side_effect=[(1,False),(0,False),(0,False)]):
            result=smoke_candidate(self.root,proposal,'Preserve existing behavior')
        self.assertEqual(result['probe'],'module_import_fallback')
        self.assertEqual(result['status'],'no_regression_observed')

    def test_failing_issue_example_uses_passing_source_behavior_before_import(self):
        proposal='diff --git a/pricing.py b/pricing.py\n'+''.join(difflib.unified_diff(
            SOURCE.splitlines(True),SOURCE.replace('x + 1','x - 1').splitlines(True),
            fromfile='a/pricing.py',tofile='b/pricing.py'))
        with patch.dict('os.environ',{'REPOPILOT_CANDIDATE_SOURCE_EXAMPLES':'1'}), patch(
                'repopilot.candidate_smoke.shutil.which',return_value='docker'), patch(
                'repopilot.candidate_smoke._run_docker',side_effect=[(1,False),(0,False),(1,False)]) as run:
            result=smoke_candidate(self.root,proposal,
                '```python\nfrom pricing import price\nassert price(1)==999\n```',timeout=30)
        self.assertEqual(result['probe'],'source_doctest_fallback')
        self.assertEqual(result['status'],'regression')
        self.assertEqual(run.call_args_list[1].args[1],run.call_args_list[2].args[1])
