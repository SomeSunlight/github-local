"""Bounded cleanup of explicitly owned directories, including Windows leftovers.

Use only for known disposable trees or files the user explicitly chose to
delete. Never suppress failures while authoritative files still exist.
"""
from __future__ import annotations

import errno
import shutil
import stat
import time
from pathlib import Path

RETRY_DELAYS = (0.0, 0.05, 0.15, 0.35)


class CleanupError(OSError):
    """Owned tree was not removed safely."""


def _real_directory(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISDIR(info.st_mode) and not (
        getattr(info, "st_file_attributes", 0) & reparse
    )


def _folders(path: Path) -> list[Path]:
    """Inspect the entire tree without traversing links or junctions."""
    if not _real_directory(path):
        raise CleanupError(f"not an ordinary owned directory: {path}")
    stack, folders = [path], []
    while stack:
        parent = stack.pop()
        folders.append(parent)
        for entry in parent.iterdir():
            if entry.is_symlink() or (
                getattr(entry.lstat(), "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            ):
                raise CleanupError(f"refusing linked/reparse entry: {entry}")
            if entry.is_dir():
                stack.append(entry)
    return folders


def remove_empty_directory(path: Path, *, delays=RETRY_DELAYS) -> bool:
    """Nonrecursive rmdir; tolerate only benign empty leftovers."""
    for index, delay in enumerate(delays):
        if index and delay:
            time.sleep(delay)
        if not path.exists() and not path.is_symlink():
            return True
        if not _real_directory(path):
            raise CleanupError(f"not an ordinary directory: {path}")
        try:
            path.rmdir()
            return True
        except OSError as exc:
            if exc.errno in (errno.ENOTEMPTY, errno.EEXIST):
                return False
    return False


def _fileless(path: Path) -> bool:
    try:
        return all(
            all(entry.is_dir() for entry in folder.iterdir())
            for folder in _folders(path)
        )
    except OSError:
        return False


def remove_owned_tree(path: Path, *, delays=RETRY_DELAYS) -> bool:
    """Remove known-owned content; fileless locked skeletons are acceptable.

    This is *not* suitable for an arbitrary user path. Nonempty failures are
    reported, and dangling symlinks/junctions are never followed.
    """
    if not path.exists() and not path.is_symlink():
        return True
    last_error: OSError | None = None
    for index, delay in enumerate(delays):
        if index and delay:
            time.sleep(delay)
        _folders(path)
        try:
            shutil.rmtree(path)
            return True
        except OSError as exc:
            last_error = exc
            if not path.exists():
                return True
            if _fileless(path):
                for folder in sorted(_folders(path), key=lambda p: len(p.parts), reverse=True):
                    remove_empty_directory(folder, delays=(0,))
                return True
    raise CleanupError(f"owned directory still contains files: {path}") from last_error
