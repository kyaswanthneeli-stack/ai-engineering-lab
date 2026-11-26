"""Copy a repository snapshot without dereferencing links."""
from pathlib import Path
from shutil import copytree
from stat import S_ISDIR, S_ISREG


class WorkspaceError(ValueError):
    pass


def copy_workspace(source: Path, destination: Path) -> None:
    excluded = {".git", ".venv", "venv", "node_modules", "__pycache__", ".runs"}

    def ignore(directory: str, names: list[str]) -> set[str]:
        skipped = excluded.intersection(names)
        for name in set(names) - skipped:
            entry = Path(directory) / name
            mode = entry.lstat().st_mode
            if not (S_ISREG(mode) or S_ISDIR(mode)):
                raise WorkspaceError("Workspace requires regular files and directories")
        return skipped

    copytree(source, destination, symlinks=True, ignore=ignore)
    if any(entry.is_symlink() for entry in destination.rglob("*")):
        raise WorkspaceError("Workspace symlink rejected")
