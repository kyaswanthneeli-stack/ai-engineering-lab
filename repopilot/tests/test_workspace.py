import tempfile
import unittest
from pathlib import Path

from repopilot.workspace import WorkspaceError, copy_workspace


class WorkspaceTests(unittest.TestCase):
    def test_excluded_directories_are_never_copied(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "original"
            source.mkdir()
            (source / "module.py").write_text("answer = 42\n")
            (source / ".runs").mkdir()
            for name in ("venv", "node_modules"):
                (source / name).symlink_to(root, target_is_directory=True)

            snapshot = root / "snapshot"
            copy_workspace(source, snapshot)

            self.assertEqual(sorted(p.name for p in snapshot.iterdir()), ["module.py"])
            self.assertEqual((snapshot / "module.py").read_text(), "answer = 42\n")

    def test_included_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "original"
            source.mkdir()
            external = root / "external.txt"
            external.write_text("local data\n")
            (source / "linked.py").symlink_to(external)

            with self.assertRaises(WorkspaceError):
                copy_workspace(source, root / "snapshot")
            self.assertFalse((root / "snapshot" / "linked.py").exists())
