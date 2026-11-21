"""Regression for Django ticket 30413. Run only inside the test container."""
from pathlib import Path
from tempfile import TemporaryDirectory

import django
from django.conf import settings

assert Path(django.__file__).resolve() == Path("/workspace/django/__init__.py")


def exercise(mode):
    with TemporaryDirectory() as temp:
        def configuration(alias):
            filename = "shared" if mode == "shared" else alias
            db = {"ENGINE": "django.db.backends.sqlite3",
                  "TEST": {"NAME": str(Path(temp) / (filename + ".sqlite3")),
                           "SERIALIZE": False}}
            if mode == "explicit":
                db["NAME"] = str(Path(temp) / (alias + "-original.sqlite3"))
            return db

        settings.configure(DATABASES={alias: configuration(alias) for alias in ("default", "other")},
                           INSTALLED_APPS=[], SECRET_KEY="offline-test", USE_I18N=False)
        django.setup()
        from django.db import connections
        from django.test.utils import setup_databases

        if mode == "identity":
            default = connections["default"]
            other = connections["other"]
            assert default.settings_dict["TEST"]["NAME"] != other.settings_dict["TEST"]["NAME"]
            if default.creation.test_db_signature() == other.creation.test_db_signature():
                raise SystemExit(42)
            return

        setup_databases(verbosity=0, interactive=False, keepdb=True)
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
