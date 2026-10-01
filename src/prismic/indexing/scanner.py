"""Filesystem scanning: discovers candidate media files under a collection root.

Extension is only a candidate filter here — actual decode validity is
Phase 4's job (see `media/formats.py` and overview section 8).
"""

from __future__ import annotations

import os
import stat
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from prismic.domain.collection import Collection
from prismic.media.formats import is_supported_extension


@dataclass(frozen=True, slots=True)
class ScannedFile:
    """A candidate media file found on disk, not yet hashed."""

    relative_path: str
    absolute_path: Path
    size: int
    mtime: float


def scan(collection: Collection) -> Iterator[ScannedFile]:
    """Recursively discover candidate media files under `collection.root`.

    Does not follow symbolic links or Windows junctions/reparse points,
    excludes the collection's own `.prismic` file, and continues past
    per-file/per-directory permission or I/O failures rather than aborting
    the whole scan. A failed or partial scan simply yields fewer files —
    callers must never interpret "not seen this scan" from a partial scan
    as "deleted"; only a reconciler acting on a *complete* scan should do
    that (see `indexing/reconciler.py`).

    Hard-link relationships are not modeled: each path is treated as an
    independent candidate regardless of inode sharing.
    """
    for entry in _walk(collection.root):
        absolute_path = Path(entry.path)
        if collection.is_collection_file(absolute_path):
            continue
        if not is_supported_extension(absolute_path):
            continue
        try:
            # Cached from the directory listing on Windows, so no extra
            # syscall per file; one `stat` on POSIX, same as before.
            stat_result = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        relative_path = absolute_path.relative_to(collection.root).as_posix()
        yield ScannedFile(
            relative_path=relative_path,
            absolute_path=absolute_path,
            size=stat_result.st_size,
            mtime=stat_result.st_mtime,
        )


def _walk(directory: Path) -> Iterator[os.DirEntry[str]]:
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return
    for entry in entries:
        try:
            if _is_reparse_point(entry):
                continue
            if entry.is_dir(follow_symlinks=False):
                yield from _walk(Path(entry.path))
            elif entry.is_file(follow_symlinks=False):
                yield entry
        except OSError:
            continue


def _is_reparse_point(entry: os.DirEntry[str]) -> bool:
    """True for symlinks (all platforms) and Windows junctions/reparse points.

    NTFS junctions aren't POSIX symlinks and `is_symlink()` doesn't detect
    them, so Windows needs its own check via the file attributes. Those come
    from the same cached directory-listing data `DirEntry` already holds, so
    unlike a separate `lstat()` per entry this costs no extra syscall.
    """
    if sys.platform == "win32":
        try:
            attributes = entry.stat(follow_symlinks=False).st_file_attributes
        except OSError:
            return False
        return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    return entry.is_symlink()
