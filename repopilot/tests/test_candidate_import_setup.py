"""Trusted import setup applies identically inside the existing Docker boundary."""
import difflib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from repopilot.candidate_smoke import _bootstrap, _failure_category, _reproducer, smoke_candidate


class CandidateImportSetupTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_setup_is_explicit_operator_opt_in(self):
        with patch.dict("os.environ", {"REPOPILOT_CANDIDATE_SMOKE_BOOTSTRAP": "0"}):
            self.assertEqual(_bootstrap(["sympy/core/basic.py"]), ("", "none"))
            self.assertEqual(_bootstrap(["django/contrib/contenttypes/fields.py"]), ("", "none"))

    def check_same_probe(self, name, setup_fragment):
        original = "value = 1\n"
        path = self.root / name
        path.parent.mkdir(parents=True)
        path.write_text(original)
        proposal = f"diff --git a/{name} b/{name}\n" + "".join(difflib.unified_diff(
            [original], ["value = 2\n"], fromfile="a/" + name, tofile="b/" + name))
        with patch.dict("os.environ", {"REPOPILOT_CANDIDATE_SMOKE_BOOTSTRAP": "1"}), patch(
                "repopilot.candidate_smoke.shutil.which", return_value="docker"), patch(
                "repopilot.candidate_smoke._run_docker", side_effect=[(0, False), (1, False)]) as runner:
            result = smoke_candidate(self.root, proposal, "Import-only validation")
        self.assertEqual(result["status"], "regression")
        self.assertEqual(runner.call_args_list[0].args[1], runner.call_args_list[1].args[1])
        self.assertIn(setup_fragment, runner.call_args_list[0].args[1])
        self.assertEqual(path.read_text(), original)

    def test_legacy_collection_aliases_are_same_for_original_and_candidate(self):
        self.check_same_probe("sympy/fixture.py", "getattr(collections.abc, _name)")

    def test_minimal_django_settings_are_same_for_original_and_candidate(self):
        self.check_same_probe("django/fixture.py", "settings.configure(INSTALLED_APPS=['django.contrib.contenttypes']")

    def test_source_layout_resolution_preserves_actual_source_origin(self):
        (self.root / "src/pkg").mkdir(parents=True)
        with patch.dict("os.environ", {"REPOPILOT_CANDIDATE_SMOKE_BOOTSTRAP": "1"}):
            script, _ = _reproducer("", ["src/pkg/fixture.py"], root=self.root)
            self.assertIn("import_module('pkg.fixture')", script)
            self.assertIn("Path('/workspace/src/pkg/fixture.py')", script)
            (self.root / "src/__init__.py").write_text("")
            script, _ = _reproducer("", ["src/pkg/fixture.py"], root=self.root)
            self.assertIn("import_module('src.pkg.fixture')", script)

    def test_public_example_is_preserved_without_injected_settings(self):
        name = "django/fixture.py"
        (self.root / "django").mkdir()
        (self.root / name).write_text("value = 1\n")
        proposal = ("diff --git a/django/fixture.py b/django/fixture.py\n"
                    "--- a/django/fixture.py\n+++ b/django/fixture.py\n"
                    "@@ -1 +1 @@\n-value = 1\n+value = 2\n")
        issue = "```python\nprint('explicit public setup')\n```"
        with patch.dict("os.environ", {"REPOPILOT_CANDIDATE_SMOKE_BOOTSTRAP": "1"}), patch(
                "repopilot.candidate_smoke.shutil.which", return_value="docker"), patch(
                "repopilot.candidate_smoke._run_docker", side_effect=[(0, False), (0, False)]) as runner:
            report = smoke_candidate(self.root, proposal, issue)
        self.assertEqual(runner.call_args_list[0].args[1], "print('explicit public setup')\n")
        self.assertEqual(report["baseline_bootstrap_profile"], "none")

    def test_detailed_known_failures_retain_only_fixed_categories(self):
        self.assertEqual(_failure_category(1,
            "ImportError: cannot import name 'Mapping' from 'collections' (/SECRET/path)"),
            "legacy_collections_api")
        self.assertEqual(_failure_category(1,
            "ImportError: cannot import name '_c_internal_utils' from partially initialized module 'matplotlib' (/SECRET)"),
            "native_extension_unavailable")
