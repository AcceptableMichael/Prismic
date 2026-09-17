"""Reconciliation: correlates a filesystem scan against recorded media identity.

Implements overview section 3's move/change semantics: new files, unchanged
files, changed content, unique vs. ambiguous moves, and missing-not-deleted
files. Also implements section 7's staleness rule: a reconciliation call for
a generation that's no longer current is a no-op, since a newer scan has
since begun.

Move detection is symmetric: a relink only happens when exactly one
"candidate" (an already-missing record, or a previously-active record whose
path wasn't seen this scan) and exactly one unmatched scanned file share a
content hash. Multiple on *either* side is treated as ambiguous — the
overview's wording ("a missing record's hash matches exactly one new file")
reads naturally as per-candidate, but the reverse case (two candidates
matching one file) is just as unsafe to guess at, so it's held to the same
1:1 standard.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from prismic.domain.collection import Collection
from prismic.domain.media import Media, MediaState
from prismic.indexing.hashing import hash_file
from prismic.indexing.scanner import scan
from prismic.persistence.repositories.media_repository import MediaRepository


@dataclass(frozen=True, slots=True)
class HashedFile:
    """A scanned file with its content hash computed."""

    relative_path: str
    content_hash: str
    size: int
    mtime: float


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    """Summary of what a reconciliation pass did.

    `applied` is False when the call was discarded as stale — a newer scan
    had already begun, so this generation's results no longer apply.
    """

    applied: bool
    new_count: int = 0
    unchanged_count: int = 0
    changed_count: int = 0
    moved_count: int = 0
    missing_count: int = 0


class Reconciler:
    """Tracks scan generations and applies reconciliation results.

    Every scan gets a generation id from `begin_scan()`. `reconcile()` only
    applies its results if that generation is still the current one — if a
    newer scan has since begun, the call is a stale no-op rather than
    mutating state out of order.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._media_repository = MediaRepository(connection)
        self._generation = 0

    def begin_scan(self) -> int:
        self._generation += 1
        return self._generation

    def reconcile(
        self,
        generation: int,
        hashed_files: Iterable[HashedFile],
        *,
        unreadable_paths: frozenset[str] = frozenset(),
    ) -> ReconciliationResult:
        """Apply one scan's results, unless a newer scan has superseded it.

        `unreadable_paths` are candidate files the scanner found but that
        failed to hash (a permission/I/O error) — their existing recorded
        state, if any, is left completely untouched this pass rather than
        being marked missing just because it couldn't be re-verified.
        """
        if generation != self._generation:
            return ReconciliationResult(applied=False)

        hashed_files = list(hashed_files)
        existing = self._media_repository.list_all()
        existing_by_path = {m.relative_path: m for m in existing if m.state == MediaState.ACTIVE}

        self._connection.execute("BEGIN")
        try:
            new_count = 0
            unchanged_count = 0
            changed_count = 0
            unmatched: list[HashedFile] = []

            for file in hashed_files:
                existing_media = existing_by_path.pop(file.relative_path, None)
                if existing_media is None:
                    unmatched.append(file)
                elif existing_media.content_hash == file.content_hash:
                    unchanged_count += 1
                else:
                    self._mark_missing(existing_media)
                    self._media_repository.create(
                        relative_path=file.relative_path,
                        content_hash=file.content_hash,
                        size=file.size,
                        mtime=file.mtime,
                        state=MediaState.ACTIVE,
                    )
                    changed_count += 1

            # Candidates for move-matching: already-missing records, plus
            # previously-active records not observed at their path this scan
            # (excluding ones that were simply unreadable this pass).
            candidates_by_hash: dict[str, list[Media]] = defaultdict(list)
            for media in existing:
                if media.state == MediaState.MISSING:
                    candidates_by_hash[media.content_hash].append(media)
            for media in existing_by_path.values():
                if media.relative_path in unreadable_paths:
                    continue
                candidates_by_hash[media.content_hash].append(media)

            files_by_hash: dict[str, list[HashedFile]] = defaultdict(list)
            for file in unmatched:
                files_by_hash[file.content_hash].append(file)

            relinked_media_ids: set[int] = set()
            moved_count = 0

            for content_hash in set(candidates_by_hash) | set(files_by_hash):
                candidates = candidates_by_hash.get(content_hash, [])
                files = files_by_hash.get(content_hash, [])
                if len(candidates) == 1 and len(files) == 1:
                    media = candidates[0]
                    file = files[0]
                    self._media_repository.update(
                        media.id,
                        relative_path=file.relative_path,
                        content_hash=file.content_hash,
                        size=file.size,
                        mtime=file.mtime,
                        state=MediaState.ACTIVE,
                    )
                    relinked_media_ids.add(media.id)
                    moved_count += 1
                else:
                    for file in files:
                        self._media_repository.create(
                            relative_path=file.relative_path,
                            content_hash=file.content_hash,
                            size=file.size,
                            mtime=file.mtime,
                            state=MediaState.ACTIVE,
                        )
                        new_count += 1

            missing_count = 0
            for media in existing_by_path.values():
                if media.id in relinked_media_ids:
                    continue
                if media.relative_path in unreadable_paths:
                    continue
                self._mark_missing(media)
                missing_count += 1
        except Exception:
            self._connection.execute("ROLLBACK")
            raise
        else:
            self._connection.execute("COMMIT")

        return ReconciliationResult(
            applied=True,
            new_count=new_count,
            unchanged_count=unchanged_count,
            changed_count=changed_count,
            moved_count=moved_count,
            missing_count=missing_count,
        )

    def _mark_missing(self, media: Media) -> None:
        if media.state == MediaState.MISSING:
            return
        self._media_repository.update(
            media.id,
            relative_path=media.relative_path,
            content_hash=media.content_hash,
            size=media.size,
            mtime=media.mtime,
            state=MediaState.MISSING,
        )


def run_reconciliation(
    reconciler: Reconciler, collection: Collection, generation: int
) -> ReconciliationResult:
    """Scan `collection.root`, hash each candidate, and reconcile the result.

    Glue between the scanner, hashing, and the reconciler. A future
    background worker (Phase 3's worker pool) dispatches this off the GUI
    thread rather than calling it inline.
    """
    hashed_files: list[HashedFile] = []
    unreadable_paths: set[str] = set()

    for scanned_file in scan(collection):
        try:
            content_hash = hash_file(scanned_file.absolute_path)
        except OSError:
            unreadable_paths.add(scanned_file.relative_path)
            continue
        hashed_files.append(
            HashedFile(
                relative_path=scanned_file.relative_path,
                content_hash=content_hash,
                size=scanned_file.size,
                mtime=scanned_file.mtime,
            )
        )

    return reconciler.reconcile(
        generation, hashed_files, unreadable_paths=frozenset(unreadable_paths)
    )
