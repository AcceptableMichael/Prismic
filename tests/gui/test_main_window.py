from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from prismic.application.commands.mapping_commands import MappingAddCommand
from prismic.ui.main_window import MainWindow


@pytest.fixture
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    return win


def _open_and_wait(qtbot: QtBot, window: MainWindow, collection_dir: Path) -> None:
    window.open_collection(collection_dir)
    qtbot.waitUntil(lambda: window.result_model.rowCount() == 2, timeout=5000)


def test_window_has_title(window: MainWindow) -> None:
    assert window.windowTitle() == "Prismic"


def test_starts_with_no_collection_open(window: MainWindow) -> None:
    assert window.session is None


def test_opening_a_collection_populates_the_result_list(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    _open_and_wait(qtbot, window, collection_dir)

    assert window.session is not None
    assert window.result_model.rowCount() == 2


def test_opening_a_bad_collection_shows_an_error_not_a_crash(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "broken"
    root.mkdir()
    (root / "broken.prismic").write_bytes(b"not a real database")

    shown_messages: list[str] = []
    monkeypatch.setattr(
        "prismic.ui.main_window.QMessageBox.critical",
        lambda *args, **kwargs: shown_messages.append(args[-1]),
    )

    window.open_collection(root)

    assert window.session is None
    assert len(shown_messages) == 1


def test_create_tag_via_the_ui_appears_in_the_filter_panel(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    _open_and_wait(qtbot, window, collection_dir)

    window._on_tag_create("vacation")

    assert [t.name for t in window.session.tags.list_all()] == ["vacation"]  # type: ignore[union-attr]
    assert window.filter_panel.model.rowCount() == 1


def test_rename_tag_via_the_ui(qtbot: QtBot, window: MainWindow, collection_dir: Path) -> None:
    _open_and_wait(qtbot, window, collection_dir)
    window._on_tag_create("vacation")
    tag = window.session.tags.list_all()[0]  # type: ignore[union-attr]

    window._on_tag_rename(tag.id, "travel")

    assert window.session.tags.get(tag.id).name == "travel"  # type: ignore[union-attr]


def test_delete_tag_via_the_ui(qtbot: QtBot, window: MainWindow, collection_dir: Path) -> None:
    _open_and_wait(qtbot, window, collection_dir)
    window._on_tag_create("vacation")
    tag = window.session.tags.list_all()[0]  # type: ignore[union-attr]

    window._on_tag_delete(tag.id)

    assert window.session.tags.list_all() == []  # type: ignore[union-attr]
    assert window.filter_panel.model.rowCount() == 0


def test_filter_selection_narrows_the_result_view(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    _open_and_wait(qtbot, window, collection_dir)
    window._on_tag_create("vacation")
    tag = window.session.tags.list_all()[0]  # type: ignore[union-attr]
    first_media = window.session.media.list_all()[0]  # type: ignore[union-attr]
    window.session.execute(  # type: ignore[union-attr]
        MappingAddCommand(media_id=first_media.id, tag_id=tag.id)
    )
    window._refresh_all()

    window._on_filter_toggle(tag.id)

    assert window.result_model.rowCount() == 1
    assert window.result_model.media_at(0).id == first_media.id

    window._on_filter_toggle(tag.id)  # deselect

    assert window.result_model.rowCount() == 2


def test_in_viewer_tag_toggle_maps_the_current_item(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    _open_and_wait(qtbot, window, collection_dir)
    window._on_tag_create("vacation")
    tag = window.session.tags.list_all()[0]  # type: ignore[union-attr]
    current_id = window.session.state.result_set[0]  # type: ignore[union-attr]
    window.session.state.current_item = current_id  # type: ignore[union-attr]
    window._refresh_all()

    window._on_item_tag_toggle(tag.id)

    assert [t.id for t in window.session.mappings.tags_for_media(current_id)] == [  # type: ignore[union-attr]
        tag.id
    ]

    window._on_item_tag_toggle(tag.id)  # toggle back off

    assert window.session.mappings.tags_for_media(current_id) == []  # type: ignore[union-attr]
