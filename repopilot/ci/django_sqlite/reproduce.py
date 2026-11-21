"""Regression for Django ticket 30413. Run only inside the test container."""
from pathlib import Path
from tempfile import TemporaryDirectory

import django
from django.conf import settings

assert Path(django.__file__).resolve() == Path("/workspace/django/__init__.py")


def exercise(mode):
    with TemporaryDirectory() as temp:
        def configuration(alias):
            filename = "shared" if mode in ("shared", "shared_setup") else alias
            db = {"ENGINE": "django.db.backends.sqlite3",
                  "TEST": {"NAME": str(Path(temp) / (filename + ".sqlite3")),
                           "SERIALIZE": False}}
            if mode == "explicit":
                db["NAME"] = str(Path(temp) / (alias + "-original.sqlite3"))
            if mode == "memory_identity":
                # Identical URI intentionally exercises memory-alias identity.
                db["TEST"]["NAME"] = "file:shared_memory?mode=memory&cache=shared"
            return db

        settings.configure(DATABASES={alias: configuration(alias) for alias in ("default", "other")},
                           INSTALLED_APPS=[], SECRET_KEY="offline-test", USE_I18N=False)
        django.setup()
        from django.db import connections
        from django.test.utils import setup_databases

        if mode in ("identity", "memory_identity"):
            default = connections["default"]
            other = connections["other"]
            first = default.settings_dict["TEST"]["NAME"]
            second = other.settings_dict["TEST"]["NAME"]
            if mode == "identity":
                assert first != second
            else:
                assert first == second and "mode=memory" in first
            if default.creation.test_db_signature() == other.creation.test_db_signature():
                raise SystemExit(42)
            return

        configured = setup_databases(verbosity=0, interactive=False, keepdb=True)
        if mode == "shared_setup":
            # Entries marked primary received create_test_db(); the other aliases are mirrors.
            # Table visibility alone can pass even if Django sets up the same file twice.
            connections.close_all()
            if sum(is_primary for _, _, is_primary in configured) != 1:
                raise SystemExit(42)
            return
        try:
            with connections["default"].cursor() as writer:
                writer.execute("CREATE TABLE repopilot_marker (id INTEGER)")
            with connections["other"].cursor() as reader:
                reader.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=%s",
                               ["repopilot_marker"])
                visible = reader.fetchone()[0] == 1
            if visible != (mode == "shared"):
                raise SystemExit(42)
        finally:
            connections.close_all()


# REPRO_MODE is supplied by the trusted host script, never by a model patch.
exercise(REPRO_MODE)
