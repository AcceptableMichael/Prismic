from pathlib import Path

import pytest

from prismic.persistence import database
from prismic.persistence.errors import IncompatibleDatabaseError


def test_connect_creates_a_new_file(tmp_path: Path) -> None:
    database_path = tmp_path / "vacation.prismic"
    connection = database.connect(database_path)
    try:
        assert database_path.exists()
    finally:
        connection.close()


def test_connect_enables_foreign_keys(tmp_path: Path) -> None:
    connection = database.connect(tmp_path / "vacation.prismic")
    try:
        row = connection.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1
    finally:
        connection.close()


def test_connect_uses_rollback_journal_not_wal(tmp_path: Path) -> None:
    connection = database.connect(tmp_path / "vacation.prismic")
    try:
        row = connection.execute("PRAGMA journal_mode").fetchone()
        assert row[0].lower() == "delete"
    finally:
        connection.close()


def test_fresh_file_has_schema_version_zero(tmp_path: Path) -> None:
    connection = database.connect(tmp_path / "vacation.prismic")
    try:
        assert database.schema_version(connection) == 0
    finally:
        connection.close()


def test_connect_rejects_a_non_database_file(tmp_path: Path) -> None:
    garbage_path = tmp_path / "not_a_database.prismic"
    garbage_path.write_bytes(b"this is not a sqlite file, just plain bytes" * 10)

    with pytest.raises(IncompatibleDatabaseError):
        database.connect(garbage_path)


def test_leaves_no_lingering_wal_or_shm_files_after_close(tmp_path: Path) -> None:
    database_path = tmp_path / "vacation.prismic"
    connection = database.connect(database_path)
    connection.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")
    connection.execute("INSERT INTO probe DEFAULT VALUES")
    connection.close()

    leftovers = list(tmp_path.glob("vacation.prismic-*"))
    assert leftovers == []
