import sqlite3
from pathlib import Path

import pytest

from prismic.persistence import database, migrations
from prismic.persistence.errors import SchemaMigrationError, SchemaTooNewError


def test_migrate_creates_schema_from_empty(tmp_path: Path) -> None:
    database_path = tmp_path / "vacation.prismic"
    connection = database.connect(database_path)
    try:
        migrations.migrate(connection, database_path)

        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        expected = {"media", "tags", "media_tags", "tag_correlations", "tag_correlation_stats"}
        assert expected <= tables
        assert database.schema_version(connection) == len(migrations.MIGRATIONS)
    finally:
        connection.close()


def test_migrate_is_a_no_op_once_at_the_current_version(tmp_path: Path) -> None:
    database_path = tmp_path / "vacation.prismic"
    connection = database.connect(database_path)
    try:
        migrations.migrate(connection, database_path)
        migrations.migrate(connection, database_path)

        assert database.schema_version(connection) == len(migrations.MIGRATIONS)
    finally:
        connection.close()


def test_migrate_rejects_a_schema_newer_than_this_build_supports(tmp_path: Path) -> None:
    database_path = tmp_path / "vacation.prismic"
    connection = database.connect(database_path)
    try:
        connection.execute(f"PRAGMA user_version = {len(migrations.MIGRATIONS) + 1}")

        with pytest.raises(SchemaTooNewError):
            migrations.migrate(connection, database_path)
    finally:
        connection.close()


def test_a_failed_migration_step_rolls_back_and_leaves_prior_schema_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "vacation.prismic"
    connection = database.connect(database_path)
    try:
        migrations.migrate(connection, database_path)
        version_before_failure = database.schema_version(connection)

        def _broken_migration(conn: sqlite3.Connection) -> None:
            conn.execute("CREATE TABLE half_created (id INTEGER PRIMARY KEY)")
            raise RuntimeError("simulated failure mid-migration")

        monkeypatch.setattr(migrations, "MIGRATIONS", [*migrations.MIGRATIONS, _broken_migration])

        with pytest.raises(SchemaMigrationError):
            migrations.migrate(connection, database_path)

        assert database.schema_version(connection) == version_before_failure
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "half_created" not in tables
        # The schema from before the failed step is still fully usable.
        connection.execute("INSERT INTO tags (name) VALUES ('still works')")
    finally:
        connection.close()
