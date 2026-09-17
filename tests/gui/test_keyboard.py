from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from prismic.ui.main_window import MainWindow


@pytest.fixture
def window(qtbot: QtBot, collection_dir: Path) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    win.open_collection(collection_dir)
    qtbot.waitUntil(lambda: win.result_model.rowCount() == 2, timeout=5000)
    return win


def test_right_arrow_navigates_to_the_next_item(qtbot: QtBot, window: MainWindow) -> None:
    session = window.session
    assert session is not None
    first_id, second_id = session.state.result_set
    session.state.current_item = first_id
    window._sync_result_selection()

    qtbot.keyClick(window, Qt.Key.Key_Right)

    assert session.state.current_item == second_id


def test_left_arrow_navigates_to_the_previous_item(qtbot: QtBot, window: MainWindow) -> None:
    session = window.session
    assert session is not None
    first_id, second_id = session.state.result_set
    session.state.current_item = second_id
    window._sync_result_selection()

    qtbot.keyClick(window, Qt.Key.Key_Left)

    assert session.state.current_item == first_id


def test_navigation_does_not_go_past_the_ends(qtbot: QtBot, window: MainWindow) -> None:
    session = window.session
    assert session is not None
    first_id, second_id = session.state.result_set
    session.state.current_item = second_id
    window._sync_result_selection()

    qtbot.keyClick(window, Qt.Key.Key_Right)  # already at the last item

    assert session.state.current_item == second_id


def test_navigation_with_no_current_item_selects_the_first(
    qtbot: QtBot, window: MainWindow
) -> None:
    session = window.session
    assert session is not None
    session.state.current_item = None

    qtbot.keyClick(window, Qt.Key.Key_Right)

    assert session.state.current_item == session.state.result_set[0]


def test_undo_shortcut_reverts_the_last_command(qtbot: QtBot, window: MainWindow) -> None:
    session = window.session
    assert session is not None
    window._on_tag_create("vacation")
    assert len(session.tags.list_all()) == 1

    qtbot.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)

    assert session.tags.list_all() == []


def test_chord_toggles_a_tag_on_the_current_item(qtbot: QtBot, window: MainWindow) -> None:
    session = window.session
    assert session is not None
    window._on_tag_create("vacation")
    tag = session.tags.list_all()[0]
    current_id = session.state.result_set[0]
    session.state.current_item = current_id

    qtbot.keyClick(window, Qt.Key.Key_T)
    assert window.keyboard.chord_is_pending is True

    qtbot.keyClick(window, Qt.Key.Key_1)

    assert window.keyboard.chord_is_pending is False
    assert [t.id for t in session.mappings.tags_for_media(current_id)] == [tag.id]


def test_escape_cancels_a_pending_chord(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.keyClick(window, Qt.Key.Key_T)
    assert window.keyboard.chord_is_pending is True

    qtbot.keyClick(window, Qt.Key.Key_Escape)

    assert window.keyboard.chord_is_pending is False


def test_a_dead_end_key_cancels_the_chord(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.keyClick(window, Qt.Key.Key_T)
    assert window.keyboard.chord_is_pending is True

    qtbot.keyClick(window, Qt.Key.Key_Q)  # not a valid continuation of any chord

    assert window.keyboard.chord_is_pending is False


def test_a_pending_chord_times_out_on_its_own(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.keyClick(window, Qt.Key.Key_T)
    assert window.keyboard.chord_is_pending is True

    qtbot.waitUntil(lambda: window.keyboard.chord_is_pending is False, timeout=3000)


def test_global_shortcuts_still_work_when_the_result_list_has_focus(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for a bug a computer-use pass caught: QAbstractItemView
    has its own built-in "type to search" behavior that swallows a plain
    letter key like "n" before it would ever reach a keyPressEvent override
    on the window itself. Earlier tests all sent keys straight to `window`
    (`qtbot.keyClick(window, ...)`), which never exercised real Qt focus
    routing through a child widget and so never caught this. Fixed by
    intercepting keys via an application-level event filter instead."""
    from PySide6.QtWidgets import QInputDialog

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("vacation", True)))

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)

    qtbot.keyClick(window.result_list, Qt.Key.Key_N)

    assert window.session is not None
    assert [t.name for t in window.session.tags.list_all()] == ["vacation"]


def test_navigation_still_works_when_the_result_list_has_focus(
    qtbot: QtBot, window: MainWindow
) -> None:
    session = window.session
    assert session is not None
    first_id, second_id = session.state.result_set
    session.state.current_item = first_id
    window._sync_result_selection()

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyClick(window.result_list, Qt.Key.Key_Right)

    assert session.state.current_item == second_id
