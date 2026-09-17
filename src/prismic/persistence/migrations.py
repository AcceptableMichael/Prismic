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
    """
    CREATE TABLE media (
        id INTEGER PRIMARY KEY,
        content_hash TEXT NOT NULL,
        relative_path TEXT NOT NULL,
        size INTEGER NOT NULL,
        mtime REAL NOT NULL,
        state TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE tags (
        id INTEGER PRIMARY KEY,
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


# Ordered by target version: MIGRATIONS[0] takes the schema from 0 to 1, and
# so on. len(MIGRATIONS) is therefore the current/target schema version.
MIGRATIONS: list[Migration] = [_migrate_to_1]


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
