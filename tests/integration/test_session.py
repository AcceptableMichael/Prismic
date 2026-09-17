from pathlib import Path

from prismic.application.commands.tag_commands import TagCreateCommand
from prismic.application.session import PrismicSession


def test_open_assembles_a_fully_working_session(tmp_path: Path) -> None:
    collection_root = tmp_path / "vacation"
    collection_root.mkdir()
    (collection_root / "a.jpg").write_bytes(b"content")

    with PrismicSession.open(collection_root) as session:
        assert session.collection.root == collection_root
        assert session.collection.database_path.exists()

        # The initial background scan eventually discovers the file.
        session.initial_reconciliation.result(timeout=5)
        session.refresh_state()

        assert len(session.media.list_all()) == 1
        assert session.state.result_set == [session.media.list_all()[0].id]


def test_commands_go_through_the_dispatcher_and_are_undoable(tmp_path: Path) -> None:
    collection_root = tmp_path / "vacation"
    collection_root.mkdir()

    with PrismicSession.open(collection_root) as session:
        session.initial_reconciliation.result(timeout=5)

        session.execute(TagCreateCommand(name="vacation"))
        assert [t.name for t in session.tags.list_all()] == ["vacation"]

        session.undo()
        assert session.tags.list_all() == []


def test_rescan_returns_a_future_and_keeps_the_database_consistent(tmp_path: Path) -> None:
    collection_root = tmp_path / "vacation"
    collection_root.mkdir()

    with PrismicSession.open(collection_root) as session:
        session.initial_reconciliation.result(timeout=5)

        (collection_root / "new.jpg").write_bytes(b"new content")
        result = session.rescan().result(timeout=5)
        session.refresh_state()

        assert result.applied
        assert [m.relative_path for m in session.media.list_all()] == ["new.jpg"]


def test_close_leaves_no_lingering_lock_for_a_subsequent_open(tmp_path: Path) -> None:
    collection_root = tmp_path / "vacation"
    collection_root.mkdir()

    session = PrismicSession.open(collection_root)
    session.initial_reconciliation.result(timeout=5)
    session.close()

    # A fresh session can open the same collection now that the first is closed.
    with PrismicSession.open(collection_root) as reopened:
        reopened.initial_reconciliation.result(timeout=5)
        assert reopened.collection.root == collection_root
