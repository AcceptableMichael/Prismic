"""Versioned, transactional schema migrations for the `.prismic` database.

The schema version is tracked in the database itself via `PRAGMA user_version`
(an integer stored in the SQLite file header), so a `.prismic` file is fully
self-describing without a separate migrations table.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from prismic.persistence.errors import SchemaMigrationError, SchemaTooNewError

Migration = Callable[[sqlite3.Connection], None]


_SCHEMA_V1_STATEMENTS = (
    # AUTOINCREMENT (not just INTEGER PRIMARY KEY) so ids are never reused
    # after a delete — move detection and undo/redo both key off of media
    # and tag ids, and a reused id could silently reattach history to the
    # wrong identity.
    """
    CREATE TABLE media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_hash TEXT NOT NULL,
        relative_path TEXT NOT NULL,
        size INTEGER NOT NULL,
        mtime REAL NOT NULL,
        state TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE media_tags (
        media_id INTEGER NOT NULL REFERENCES media(id),
        tag_id INTEGER NOT NULL REFERENCES tags(id),
        PRIMARY KEY (media_id, tag_id)
    )
    """,
    "CREATE INDEX idx_media_relative_path ON media(relative_path)",
    "CREATE INDEX idx_media_content_hash ON media(content_hash)",
    "CREATE INDEX idx_media_tags_media ON media_tags(media_id)",
    "CREATE INDEX idx_media_tags_tag ON media_tags(tag_id)",
)


def _migrate_to_1(connection: sqlite3.Connection) -> None:
    # Individual execute() calls, not executescript(): executescript() issues
    # its own implicit COMMIT before running, which would silently close the
    # manually-managed transaction migrate() wraps each step in.
    for statement in _SCHEMA_V1_STATEMENTS:
        connection.execute(statement)


# Singleton row (id is always 1) holding the file count from the most
# recently *completed* scan of this collection -- used as the denominator
# for a progress indicator on the *next* scan, since a scan in progress has
# no way to know its own total ahead of time (see ScanStatsRepository).
_SCHEMA_V2_STATEMENTS = (
    """
    CREATE TABLE scan_stats (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        last_file_count INTEGER NOT NULL
    )
    """,
    "INSERT INTO scan_stats (id, last_file_count) VALUES (1, 0)",
)


def _migrate_to_2(connection: sqlite3.Connection) -> None:
    for statement in _SCHEMA_V2_STATEMENTS:
        connection.execute(statement)


# `tag_correlations` is a materialized, directional (tag_x_id -> tag_y_id)
# cache of how often two tags co-occur, rebuilt wholesale by
# `TagCorrelationRepository.recompute()` rather than kept incrementally in
# sync with every tag/mapping change -- see that class for why. Raw counts
# are stored (not a precomputed ratio/threshold decision) so a later change
# to the correlation-percentage setting takes effect immediately, without
# needing a recompute of its own.
#
# `tag_correlation_stats` is a `scan_stats`-style singleton row recording
# when that cache was last rebuilt, so a caller can throttle how often a
# full recompute happens without needing its own separate persistence.
_SCHEMA_V3_STATEMENTS = (
    """
    CREATE TABLE tag_correlations (
        tag_x_id INTEGER NOT NULL REFERENCES tags(id),
        tag_y_id INTEGER NOT NULL REFERENCES tags(id),
        both_count INTEGER NOT NULL,
        x_count INTEGER NOT NULL,
        PRIMARY KEY (tag_x_id, tag_y_id)
    )
    """,
    """
    CREATE TABLE tag_correlation_stats (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        computed_at REAL
    )
    """,
    "INSERT INTO tag_correlation_stats (id, computed_at) VALUES (1, NULL)",
)


def _migrate_to_3(connection: sqlite3.Connection) -> None:
    for statement in _SCHEMA_V3_STATEMENTS:
        connection.execute(statement)


# Ordered by target version: MIGRATIONS[0] takes the schema from 0 to 1, and
# so on. len(MIGRATIONS) is therefore the current/target schema version.
MIGRATIONS: list[Migration] = [_migrate_to_1, _migrate_to_2, _migrate_to_3]


def migrate(connection: sqlite3.Connection, database_path: Path) -> None:
    """Bring the database up to the current schema version.

    Each migration step runs in its own transaction; a failing step rolls
    back cleanly, leaving the previous valid schema (and version) intact
    rather than a partially-migrated database.
    """
    current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    target_version = len(MIGRATIONS)

    if current_version > target_version:
        raise SchemaTooNewError(database_path, current_version, target_version)

    for version in range(current_version, target_version):
        migration = MIGRATIONS[version]
        connection.execute("BEGIN")
        try:
            migration(connection)
            connection.execute(f"PRAGMA user_version = {version + 1}")
        except Exception as exc:
            connection.execute("ROLLBACK")
            raise SchemaMigrationError(
                f"Migration to schema version {version + 1} failed for {database_path}: {exc}"
            ) from exc
        else:
            connection.execute("COMMIT")
