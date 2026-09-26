import sqlite3
from pathlib import Path

import pytest

from prismic.domain.collection import Collection
from prismic.domain.media import MediaState
from prismic.indexing.reconciler import HashedFile, Reconciler, run_reconciliation
from prismic.persistence.repositories.media_repository import MediaRepository
from prismic.persistence.repositories.scan_stats_repository import ScanStatsRepository


@pytest.fixture
def collection(tmp_path: Path) -> Collection:
    return Collection(root=tmp_path, database_path=tmp_path / "vacation.prismic")


@pytest.fixture
def reconciler() -> Reconciler:
    return Reconciler()


@pytest.fixture
def media_repository(migrated_connection: sqlite3.Connection) -> MediaRepository:
    return MediaRepository(migrated_connection)


def _run(reconciler: Reconciler, collection: Collection, connection: sqlite3.Connection) -> None:
    generation = reconciler.begin_scan()
    result = run_reconciliation(reconciler, collection, generation, connection)
    assert result.applied


def test_new_file_gets_a_new_identity(
    collection: Collection,
    reconciler: Reconciler,
    media_repository: MediaRepository,
    migrated_connection: sqlite3.Connection,
) -> None:
    (collection.root / "a.jpg").write_bytes(b"content")

    _run(reconciler, collection, migrated_connection)

    media = media_repository.list_all()
    assert len(media) == 1
    assert media[0].relative_path == "a.jpg"
    assert media[0].state == MediaState.ACTIVE


def test_unchanged_file_is_a_no_op(
    collection: Collection,
    reconciler: Reconciler,
    media_repository: MediaRepository,
    migrated_connection: sqlite3.Connection,
) -> None:
    (collection.root / "a.jpg").write_bytes(b"content")
    _run(reconciler, collection, migrated_connection)
    first_pass = media_repository.list_all()

    _run(reconciler, collection, migrated_connection)

    second_pass = media_repository.list_all()
    assert second_pass == first_pass


def test_changed_content_creates_a_new_identity_and_retires_the_old_one(
    collection: Collection,
    reconciler: Reconciler,
    media_repository: MediaRepository,
    migrated_connection: sqlite3.Connection,
) -> None:
    target = collection.root / "a.jpg"
    target.write_bytes(b"original content")
    _run(reconciler, collection, migrated_connection)
    original = media_repository.list_all()[0]

    target.write_bytes(b"replaced content")
    _run(reconciler, collection, migrated_connection)

    media = media_repository.list_all()
    assert len(media) == 2
    retired = next(m for m in media if m.id == original.id)
    replacement = next(m for m in media if m.id != original.id)
    assert retired.state == MediaState.MISSING
    assert retired.content_hash == original.content_hash  # untouched history
    assert replacement.relative_path == "a.jpg"
    assert replacement.state == MediaState.ACTIVE
    assert replacement.content_hash != original.content_hash


def test_unique_move_relinks_the_existing_identity(
    collection: Collection,
    reconciler: Reconciler,
    media_repository: MediaRepository,
    migrated_connection: sqlite3.Connection,
) -> None:
    original_path = collection.root / "a.jpg"
    original_path.write_bytes(b"content")
    _run(reconciler, collection, migrated_connection)
    original = media_repository.list_all()[0]

    original_path.rename(collection.root / "moved.jpg")
    _run(reconciler, collection, migrated_connection)

    media = media_repository.list_all()
    assert len(media) == 1
    assert media[0].id == original.id
    assert media[0].relative_path == "moved.jpg"
    assert media[0].state == MediaState.ACTIVE


def test_ambiguous_move_leaves_the_old_identity_unresolved(
    collection: Collection,
    reconciler: Reconciler,
    media_repository: MediaRepository,
    migrated_connection: sqlite3.Connection,
) -> None:
    original_path = collection.root / "a.jpg"
    original_path.write_bytes(b"shared content")
    _run(reconciler, collection, migrated_connection)
    original = media_repository.list_all()[0]

    # The original disappears from its path, and two *different* new files
    # both happen to share its content hash — Prismic must not guess which
    # (if either) is "the move".
    original_path.unlink()
    (collection.root / "candidate_one.jpg").write_bytes(b"shared content")
    (collection.root / "candidate_two.jpg").write_bytes(b"shared content")
    _run(reconciler, collection, migrated_connection)

    media = media_repository.list_all()
    assert len(media) == 3
    original_after = next(m for m in media if m.id == original.id)
    assert original_after.state == MediaState.MISSING
    new_identities = [m for m in media if m.id != original.id]
    assert len(new_identities) == 2
    assert {m.relative_path for m in new_identities} == {"candidate_one.jpg", "candidate_two.jpg"}
    assert all(m.state == MediaState.ACTIVE for m in new_identities)


def test_missing_file_is_marked_missing_not_deleted(
    collection: Collection,
    reconciler: Reconciler,
    media_repository: MediaRepository,
    migrated_connection: sqlite3.Connection,
) -> None:
    target = collection.root / "a.jpg"
    target.write_bytes(b"content")
    _run(reconciler, collection, migrated_connection)
    original = media_repository.list_all()[0]

    target.unlink()
    _run(reconciler, collection, migrated_connection)

    media = media_repository.list_all()
    assert len(media) == 1
    assert media[0].id == original.id
    assert media[0].state == MediaState.MISSING


def test_unsupported_file_is_never_recorded(
    collection: Collection,
    reconciler: Reconciler,
    media_repository: MediaRepository,
    migrated_connection: sqlite3.Connection,
) -> None:
    (collection.root / "notes.txt").write_bytes(b"not media")

    _run(reconciler, collection, migrated_connection)

    assert media_repository.list_all() == []


def test_unreadable_file_is_skipped_without_disturbing_its_recorded_state(
    collection: Collection,
    reconciler: Reconciler,
    media_repository: MediaRepository,
    migrated_connection: sqlite3.Connection,
) -> None:
    target = collection.root / "a.jpg"
    target.write_bytes(b"content")
    _run(reconciler, collection, migrated_connection)
    original = media_repository.list_all()[0]

    generation = reconciler.begin_scan()
    result = reconciler.reconcile(
        migrated_connection, generation, [], unreadable_paths=frozenset({"a.jpg"})
    )

    assert result.applied
    media = media_repository.list_all()
    assert media == [original]  # left completely untouched, not marked missing


def test_a_stale_reconciliation_is_discarded(
    reconciler: Reconciler,
    media_repository: MediaRepository,
    migrated_connection: sqlite3.Connection,
) -> None:
    stale_generation = reconciler.begin_scan()
    current_generation = reconciler.begin_scan()  # a newer scan has since begun

    result = reconciler.reconcile(
        migrated_connection,
        stale_generation,
        [HashedFile(relative_path="a.jpg", content_hash="h", size=1, mtime=1.0)],
    )

    assert result.applied is False
    assert media_repository.list_all() == []

    # The current generation still applies normally.
    result = reconciler.reconcile(
        migrated_connection,
        current_generation,
        [HashedFile(relative_path="a.jpg", content_hash="h", size=1, mtime=1.0)],
    )
    assert result.applied is True
    assert len(media_repository.list_all()) == 1


def test_scan_reports_progress_against_the_previous_scans_count(
    collection: Collection,
    reconciler: Reconciler,
    migrated_connection: sqlite3.Connection,
) -> None:
    (collection.root / "a.jpg").write_bytes(b"content")
    (collection.root / "b.jpg").write_bytes(b"more content")
    _run(reconciler, collection, migrated_connection)  # first scan: no prior count to report

    (collection.root / "c.jpg").write_bytes(b"even more content")
    calls: list[tuple[int, int]] = []
    generation = reconciler.begin_scan()
    run_reconciliation(
        reconciler,
        collection,
        generation,
        migrated_connection,
        on_progress=lambda processed, total: calls.append((processed, total)),
    )

    # Three candidate files this pass, each reported as it's processed,
    # against last scan's total (2) as the denominator throughout.
    assert len(calls) == 3
    assert {processed for processed, _ in calls} == {1, 2, 3}
    assert all(expected_total == 2 for _, expected_total in calls)


def test_scan_persists_its_own_file_count_for_the_next_scan_to_use(
    collection: Collection,
    reconciler: Reconciler,
    migrated_connection: sqlite3.Connection,
) -> None:
    (collection.root / "a.jpg").write_bytes(b"content")
    (collection.root / "b.jpg").write_bytes(b"more content")

    _run(reconciler, collection, migrated_connection)

    assert ScanStatsRepository(migrated_connection).get_last_file_count() == 2


def test_reconciliation_can_run_on_a_separate_connection_to_the_same_file(
    tmp_path: Path,
) -> None:
    """The whole point of taking a connection per call: a background worker
    opens its own connection to the same `.prismic` file rather than reusing
    the session's main-thread connection."""
    from prismic.persistence import database, migrations

    database_path = tmp_path / "vacation.prismic"
    main_connection = database.connect(database_path)
    migrations.migrate(main_connection, database_path)

    collection = Collection(root=tmp_path, database_path=database_path)
    (tmp_path / "a.jpg").write_bytes(b"content")

    worker_connection = database.connect(database_path)
    try:
        reconciler = Reconciler()
        generation = reconciler.begin_scan()
        result = run_reconciliation(reconciler, collection, generation, worker_connection)
        assert result.applied
    finally:
        worker_connection.close()

    media = MediaRepository(main_connection).list_all()
    assert len(media) == 1
    assert media[0].relative_path == "a.jpg"
    main_connection.close()
