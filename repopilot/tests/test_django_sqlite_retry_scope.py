"""Tests for the explicitly assisted Django SQLite retry's guarded source scope."""
import tempfile
import unittest
from pathlib import Path

from ci.django_sqlite.retry import (
    ALIAS_PATCH, MODES, OLD_PATCH, eligible_for_official_scoring,
    failure_clues, known_failed_hashes, method_anchors,
)


class DjangoSQLiteRetryScopeTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.repo = Path(self.work.name)
        self.file = self.repo / "django/db/backends/sqlite3/creation.py"
        self.file.parent.mkdir(parents=True)

    def write_source(self, body):
        self.file.write_text(
            "class DatabaseCreation:\n"
            "    def test_db_signature(self):\n"
            "        test_database_name = self._get_test_db_name()\n"
            "        sig = [self.connection.settings_dict['NAME']]\n"
            + body +
            "        return tuple(sig)\n",
            encoding="utf-8",
        )

    def test_only_file_vs_memory_branch_is_allowed_for_exact_edits(self):
        self.write_source(
            "        if self.is_in_memory_db(test_database_name):\n"
            "            sig.append(self.connection.alias)\n"
        )
        anchors = method_anchors(self.repo)
        self.assertEqual(len(anchors), 1)
        self.assertIn("is_in_memory_db(test_database_name)", anchors[0])
        self.assertIn("sig.append(self.connection.alias)", anchors[0])
        self.assertNotIn("sig = [", anchors[0])
        self.assertNotIn("return tuple(sig)", anchors[0])

    def test_missing_decision_branch_fails_closed(self):
        self.write_source("        sig.append(self.connection.alias)\n")
        with self.assertRaisesRegex(ValueError, "one unique in-memory branch"):
            method_anchors(self.repo)

    def test_multiple_memory_decisions_fail_closed(self):
        self.write_source(
            "        if self.is_in_memory_db(test_database_name):\n"
            "            sig.append(self.connection.alias)\n"
            "        if self.is_in_memory_db(test_database_name):\n"
            "            sig.append(test_database_name)\n"
        )
        with self.assertRaisesRegex(ValueError, "one unique in-memory branch"):
            method_anchors(self.repo)
    
    def test_probe_failure_feedback_separates_disk_and_memory_requirements(self):
        codes = {mode: 0 for mode in MODES}
        codes["shared_setup"] = 42
        message = failure_clues(codes)
        self.assertIn("initialized twice", message)
        self.assertNotIn("Different persistent", message)

        codes["shared_setup"] = 0
        codes["distinct"] = 42
        message = failure_clues(codes)
        self.assertIn("Different persistent", message)
        self.assertNotIn("initialized twice", message)

        codes["distinct"] = 0
        codes["memory_identity"] = 42
        self.assertIn("In-memory aliases", failure_clues(codes))

    def test_probe_feedback_rejects_missing_or_invalid_modes(self):
        self.assertIn("passed", failure_clues({mode: 0 for mode in MODES}))
        with self.assertRaisesRegex(ValueError, "Invalid SQLite"):
            failure_clues({"distinct": 42})
        with self.assertRaisesRegex(ValueError, "Invalid SQLite"):
            failure_clues({mode: "0" for mode in MODES})

    def test_history_contains_prior_independently_failed_patches(self):
        hashes = known_failed_hashes()
        self.assertIn(OLD_PATCH, hashes)
        self.assertIn(ALIAS_PATCH, hashes)
        self.assertEqual(len(hashes), 5)
        self.assertIn("71abf48b6514d36af5ca9d4ab665bdc978549b1647a119c736f7488a42ee02fa", hashes)

    def test_history_fails_closed_when_a_confirmed_failure_is_missing(self):
        import json
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / "failed.json"
            original = json.loads(
                (Path(__file__).parents[1] /
                 "ci/django_sqlite/known_failed_patches.json").read_text()
            )
            original["failed"] = original["failed"][1:]
            ledger.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError, "Required prior failed"):
                known_failed_hashes(ledger)

    def test_only_six_clean_probes_are_officially_eligible(self):
        clean = {mode: 0 for mode in MODES}
        self.assertTrue(eligible_for_official_scoring(clean))
        for mode in MODES:
            with self.subTest(mode=mode):
                failed = {**clean, mode: 42}
                self.assertFalse(eligible_for_official_scoring(failed))
        with self.assertRaisesRegex(ValueError, "Invalid SQLite"):
            eligible_for_official_scoring({"distinct": 0})

    def test_feedback_distinguishes_persistent_and_shared_memory_storage(self):
        from ci.django_sqlite.retry import FEEDBACK
        self.assertIn("SAME in-memory URI", FEEDBACK)
        self.assertIn("unconditional filename", FEEDBACK)
        self.assertIn("two aliases sharing one persistent file", FEEDBACK)
        self.assertIn("different persistent files", FEEDBACK)

