import sqlite3

from prismic.persistence.repositories.scan_stats_repository import ScanStatsRepository


def test_starts_at_zero_for_a_freshly_migrated_database(migrated_connection: sqlite3.Connection) -> None:
    assert ScanStatsRepository(migrated_connection).get_last_file_count() == 0


def test_set_then_get_round_trips(migrated_connection: sqlite3.Connection) -> None:
    repository = ScanStatsRepository(migrated_connection)

    repository.set_last_file_count(42)

    assert repository.get_last_file_count() == 42


def test_set_overwrites_the_singleton_row_rather_than_adding_another(
    migrated_connection: sqlite3.Connection,
) -> None:
    repository = ScanStatsRepository(migrated_connection)

    repository.set_last_file_count(1)
    repository.set_last_file_count(2)

    assert repository.get_last_file_count() == 2
    row_count = migrated_connection.execute("SELECT COUNT(*) AS n FROM scan_stats").fetchone()["n"]
    assert row_count == 1
