"""End-to-end coverage for bulk file selection: additive shift/ctrl-click
in the result list, the tag-intersection editing it drives, and the grid
display that replaces the single-item viewer while more than one file is
selected.
"""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from prismic.ui.main_window import MainWindow
from prismic.ui.tag_model import CheckedRole


@pytest.fixture
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    return win


def _open_and_wait(qtbot: QtBot, window: MainWindow, collection_dir: Path) -> None:
    window.open_collection(collection_dir)
    qtbot.waitUntil(lambda: window.result_model.rowCount() == 2, timeout=5000)


def _select_both(window: MainWindow) -> tuple[int, int]:
    assert window.session is not None
    a_id, b_id = window.session.state.result_set
    window.session.state.current_item = b_id
    window.session.state.selected_items = frozenset({a_id, b_id})
    window._refresh_all()
    return a_id, b_id


def _checked_tag_names(window: MainWindow) -> set[str]:
    model = window.item_tag_panel.model
    return {
        model.tag_at(row).name
        for row in range(model.rowCount())
        if model.data(model.index(row, 0), CheckedRole)
    }


def _click(qtbot: QtBot, window: MainWindow, row: int, modifier: Qt.KeyboardModifier) -> None:
    index = window.result_model.index(row, 0)
    rect = window.result_list.visualRect(index)
    qtbot.mouseClick(
        window.result_list.viewport(), Qt.MouseButton.LeftButton, modifier, pos=rect.center()
    )


# -- The grid replaces the viewer for a multi-selection -----------------------


def test_selecting_two_items_shows_the_grid_instead_of_the_viewer(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    _open_and_wait(qtbot, window, collection_dir)

    _select_both(window)

    assert window._media_stack.currentWidget() is window.selection_grid


def test_a_single_selection_shows_the_ordinary_viewer(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    _open_and_wait(qtbot, window, collection_dir)
    a_id, _b_id = _select_both(window)

    window.session.state.current_item = a_id  # type: ignore[union-attr]
    window.session.state.selected_items = frozenset({a_id})  # type: ignore[union-attr]
    window._refresh_all()

    assert window._media_stack.currentWidget() is window.viewer


# -- Additive selection through real clicks on the result list ----------------


def test_ctrl_click_through_the_real_list_selects_both_and_shows_the_grid(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    _open_and_wait(qtbot, window, collection_dir)

    _click(qtbot, window, 0, Qt.KeyboardModifier.NoModifier)
    _click(qtbot, window, 1, Qt.KeyboardModifier.ControlModifier)

    assert window.session.state.selected_items == frozenset(window.session.state.result_set)  # type: ignore[union-attr]
    assert window._media_stack.currentWidget() is window.selection_grid


def test_a_later_plain_click_collapses_back_to_a_single_item(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    _open_and_wait(qtbot, window, collection_dir)
    _click(qtbot, window, 0, Qt.KeyboardModifier.NoModifier)
    _click(qtbot, window, 1, Qt.KeyboardModifier.ControlModifier)

    _click(qtbot, window, 0, Qt.KeyboardModifier.NoModifier)

    assert window.session.state.selected_items == {window.session.state.result_set[0]}  # type: ignore[union-attr]
    assert window._media_stack.currentWidget() is window.viewer


# -- Multi-select tag editing shows/writes the intersection -------------------


def test_multi_select_tag_panel_shows_only_tags_common_to_every_selected_file(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    _open_and_wait(qtbot, window, collection_dir)
    a_id, b_id = window.session.state.result_set  # type: ignore[union-attr]
    window._on_tag_create("kittens")
    window._on_tag_create("beach")
    tags_by_name = {t.name: t.id for t in window.session.tags.list_all()}  # type: ignore[union-attr]
    window.session.mappings.add(a_id, tags_by_name["kittens"])  # type: ignore[union-attr]
    window.session.mappings.add(b_id, tags_by_name["kittens"])  # type: ignore[union-attr]
    window.session.mappings.add(a_id, tags_by_name["beach"])  # type: ignore[union-attr]  # only a has it

    _select_both(window)

    assert _checked_tag_names(window) == {"kittens"}


def test_toggling_a_common_tag_removes_it_from_every_selected_file(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    _open_and_wait(qtbot, window, collection_dir)
    a_id, b_id = window.session.state.result_set  # type: ignore[union-attr]
    window._on_tag_create("kittens")
    kittens = window.session.tags.list_all()[0]  # type: ignore[union-attr]
    window.session.mappings.add(a_id, kittens.id)  # type: ignore[union-attr]
    window.session.mappings.add(b_id, kittens.id)  # type: ignore[union-attr]
    _select_both(window)

    window._on_item_tag_toggle(kittens.id)

    assert window.session.mappings.tags_for_media(a_id) == []  # type: ignore[union-attr]
    assert window.session.mappings.tags_for_media(b_id) == []  # type: ignore[union-attr]


def test_toggling_a_non_common_tag_adds_it_to_every_selected_file(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    """The product's own example: selecting "beach" while both files are
    selected and only one already has it must leave both with it."""
    _open_and_wait(qtbot, window, collection_dir)
    a_id, b_id = window.session.state.result_set  # type: ignore[union-attr]
    window._on_tag_create("beach")
    beach = window.session.tags.list_all()[0]  # type: ignore[union-attr]
    window.session.mappings.add(a_id, beach.id)  # type: ignore[union-attr]  # only a has it
    _select_both(window)

    window._on_item_tag_toggle(beach.id)

    assert [t.id for t in window.session.mappings.tags_for_media(a_id)] == [beach.id]  # type: ignore[union-attr]
    assert [t.id for t in window.session.mappings.tags_for_media(b_id)] == [beach.id]  # type: ignore[union-attr]


def test_undoing_a_multi_select_add_is_one_step_and_only_reverts_what_changed(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    _open_and_wait(qtbot, window, collection_dir)
    a_id, b_id = window.session.state.result_set  # type: ignore[union-attr]
    window._on_tag_create("beach")
    beach = window.session.tags.list_all()[0]  # type: ignore[union-attr]
    window.session.mappings.add(a_id, beach.id)  # type: ignore[union-attr]  # only a has it, going in
    _select_both(window)
    window._on_item_tag_toggle(beach.id)  # adds it to b too, one undo step

    window._undo()

    assert [t.id for t in window.session.mappings.tags_for_media(a_id)] == [beach.id]  # type: ignore[union-attr]
    assert window.session.mappings.tags_for_media(b_id) == []  # type: ignore[union-attr]
