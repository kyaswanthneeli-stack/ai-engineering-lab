"""Tests for the explicitly assisted Django SQLite retry's guarded source scope."""
import tempfile
import unittest
from pathlib import Path

from ci.django_sqlite.retry import method_anchors


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
