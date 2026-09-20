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


def test_down_arrow_navigates_to_the_next_item(qtbot: QtBot, window: MainWindow) -> None:
    session = window.session
    assert session is not None
    first_id, second_id = session.state.result_set
    session.state.current_item = first_id
    window._sync_result_selection()

    qtbot.keyClick(window, Qt.Key.Key_Down)

    assert session.state.current_item == second_id


def test_up_arrow_navigates_to_the_previous_item(qtbot: QtBot, window: MainWindow) -> None:
    session = window.session
    assert session is not None
    first_id, second_id = session.state.result_set
    session.state.current_item = second_id
    window._sync_result_selection()

    qtbot.keyClick(window, Qt.Key.Key_Up)

    assert session.state.current_item == first_id


def test_up_down_navigate_even_while_a_tag_search_box_has_focus(
    qtbot: QtBot, window: MainWindow
) -> None:
    """Unlike every other global shortcut, Up/Down deliberately aren't
    exempted while text-editing has focus -- they have no meaning in a
    single-line box (unlike Left/Right, which move the caret), so result-
    list navigation should stay reachable no matter where the caret is."""
    session = window.session
    assert session is not None
    first_id, second_id = session.state.result_set
    session.state.current_item = first_id
    window._sync_result_selection()

    window.item_tag_panel.search_box.setFocus()
    qtbot.waitUntil(lambda: window.item_tag_panel.search_box.hasFocus(), timeout=1000)

    qtbot.keyClick(window.item_tag_panel.search_box, Qt.Key.Key_Down)
    assert session.state.current_item == second_id

    qtbot.keyClick(window.item_tag_panel.search_box, Qt.Key.Key_Up)
    assert session.state.current_item == first_id

    # A plain letter, by contrast, must still land in the box as text --
    # confirms the exemption is narrowly scoped to Up/Down, not blanket.
    qtbot.keyClick(window.item_tag_panel.search_box, Qt.Key.Key_A)
    assert window.item_tag_panel.search_box.text() == "a"


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


def test_global_shortcuts_still_work_when_the_result_list_has_focus(
    qtbot: QtBot, window: MainWindow
) -> None:
    """Regression test for a bug a computer-use pass caught: QAbstractItemView
    has its own built-in "type to search" behavior that swallows a plain
    letter key before it would ever reach a keyPressEvent override on the
    window itself. Earlier tests all sent keys straight to `window`
    (`qtbot.keyClick(window, ...)`), which never exercised real Qt focus
    routing through a child widget and so never caught this. Fixed by
    intercepting keys via an application-level event filter instead.

    "Tab" immediately focuses the item-tag ("Edit this file") search box
    (see `KeyboardController`'s `on_focus_item_tags` wiring in
    `MainWindow`) -- typing a name there and pressing Enter is what
    actually creates (and applies) the tag, exercised in
    `test_main_window.py`. A second "Tab", once focus is already inside
    that box, cycles to the filter search box instead -- that redirect is
    `MainWindow.eventFilter`/`_cycle_tag_search_focus`'s doing, checked
    ahead of ever calling into `KeyboardController`. A third "Tab" is a
    hidden third step in that cycle: it dismisses typing focus back to the
    result list rather than looping straight back to the first box, so a
    Tab-Tab-Tab burst always ends up not typing, instead of still typing in
    a different search box."""
    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)

    qtbot.keyClick(window.result_list, Qt.Key.Key_Tab)

    assert window.item_tag_panel.search_box.hasFocus()

    qtbot.keyClick(window.item_tag_panel.search_box, Qt.Key.Key_Tab)

    assert window.filter_panel.search_box.hasFocus()

    qtbot.keyClick(window.filter_panel.search_box, Qt.Key.Key_Tab)

    assert window.result_list.hasFocus()  # dismissed, not cycled back

    qtbot.keyClick(window.result_list, Qt.Key.Key_Tab)

    assert window.item_tag_panel.search_box.hasFocus()  # loop starts over


def test_escape_dismisses_typing_focus_from_either_search_box(
    qtbot: QtBot, window: MainWindow
) -> None:
    window.item_tag_panel.search_box.setFocus()
    qtbot.waitUntil(lambda: window.item_tag_panel.search_box.hasFocus(), timeout=1000)

    qtbot.keyClick(window.item_tag_panel.search_box, Qt.Key.Key_Escape)

    assert window.result_list.hasFocus()

    window.filter_panel.search_box.setFocus()
    qtbot.waitUntil(lambda: window.filter_panel.search_box.hasFocus(), timeout=1000)

    qtbot.keyClick(window.filter_panel.search_box, Qt.Key.Key_Escape)

    assert window.result_list.hasFocus()


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


def test_space_toggles_focus_mode_hiding_every_panel_but_the_viewer(
    qtbot: QtBot, window: MainWindow
) -> None:
    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    assert window.result_list.isVisible()
    assert window._tag_splitter.isVisible()

    qtbot.keyClick(window.result_list, Qt.Key.Key_Space)

    assert window._focus_mode_action.isChecked() is True
    assert window.result_list.isVisible() is False
    assert window._tag_splitter.isVisible() is False
    assert window.menuBar().isVisible() is False
    assert window.statusBar().isVisible() is False
    assert window.viewer.isVisible()  # the one thing that stays

    qtbot.keyClick(window.result_list, Qt.Key.Key_Space)

    assert window._focus_mode_action.isChecked() is False
    assert window.result_list.isVisible()
    assert window._tag_splitter.isVisible()


def test_escape_exits_focus_mode(qtbot: QtBot, window: MainWindow) -> None:
    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyClick(window.result_list, Qt.Key.Key_Space)
    assert window._focus_mode_action.isChecked() is True

    qtbot.keyClick(window.result_list, Qt.Key.Key_Escape)

    assert window._focus_mode_action.isChecked() is False
    assert window.result_list.isVisible()


def test_opening_a_collection_resets_focus_mode(
    qtbot: QtBot, window: MainWindow, collection_dir: Path
) -> None:
    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyClick(window.result_list, Qt.Key.Key_Space)
    assert window._focus_mode_action.isChecked() is True

    window.open_collection(collection_dir)

    assert window._focus_mode_action.isChecked() is False
    assert window.result_list.isVisible()


def test_digit_toggles_the_unselected_tag_numbered_with_it(
    qtbot: QtBot, window: MainWindow
) -> None:
    session = window.session
    assert session is not None
    current_id = session.state.result_set[0]
    session.state.current_item = current_id
    window._on_tag_create("a")
    window._on_tag_create("b")
    assert window._tag_shortcut_mode_action.isChecked() is False  # unselected by default
    tag_id = window.item_tag_panel.model.tag_id_for_shortcut(1, selected=False)
    assert tag_id is not None

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyClick(window.result_list, Qt.Key.Key_1)

    assert [t.id for t in session.mappings.tags_for_media(current_id)] == [tag_id]


def test_digit_toggles_a_tag_even_while_a_search_box_is_focused(
    qtbot: QtBot, window: MainWindow
) -> None:
    session = window.session
    assert session is not None
    current_id = session.state.result_set[0]
    session.state.current_item = current_id
    window._on_tag_create("a")
    tag_id = window.item_tag_panel.model.tag_id_for_shortcut(1, selected=False)
    assert tag_id is not None

    window.item_tag_panel.search_box.setFocus()
    qtbot.waitUntil(lambda: window.item_tag_panel.search_box.hasFocus(), timeout=1000)
    qtbot.keyClick(window.item_tag_panel.search_box, Qt.Key.Key_1)

    assert window.item_tag_panel.search_box.text() == ""  # not typed
    assert [t.id for t in session.mappings.tags_for_media(current_id)] == [tag_id]

    # Also true from the *filter* search box, per the request this
    # implements -- the toggle still applies to the Edit list regardless
    # of which of the two boxes has focus.
    window._on_item_tag_toggle(tag_id)  # untoggle it again
    window.filter_panel.search_box.setFocus()
    qtbot.waitUntil(lambda: window.filter_panel.search_box.hasFocus(), timeout=1000)
    qtbot.keyClick(window.filter_panel.search_box, Qt.Key.Key_1)

    assert window.filter_panel.search_box.text() == ""
    assert [t.id for t in session.mappings.tags_for_media(current_id)] == [tag_id]


def test_ctrl_digit_types_a_literal_digit_instead_of_toggling(
    qtbot: QtBot, window: MainWindow
) -> None:
    session = window.session
    assert session is not None
    session.state.current_item = session.state.result_set[0]
    window._on_tag_create("a")

    window.item_tag_panel.search_box.setFocus()
    qtbot.waitUntil(lambda: window.item_tag_panel.search_box.hasFocus(), timeout=1000)
    qtbot.keyClick(
        window.item_tag_panel.search_box, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier
    )

    assert window.item_tag_panel.search_box.text() == "1"
    assert session.mappings.tags_for_media(session.state.current_item) == []


def test_ctrl_tapped_alone_toggles_which_tags_are_numbered(
    qtbot: QtBot, window: MainWindow
) -> None:
    assert window._tag_shortcut_mode_action.isChecked() is False

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyPress(window.result_list, Qt.Key.Key_Control)
    qtbot.keyRelease(window.result_list, Qt.Key.Key_Control)

    assert window._tag_shortcut_mode_action.isChecked() is True

    qtbot.keyPress(window.result_list, Qt.Key.Key_Control)
    qtbot.keyRelease(window.result_list, Qt.Key.Key_Control)

    assert window._tag_shortcut_mode_action.isChecked() is False


def test_ctrl_plus_another_key_does_not_toggle_the_mode_on_release(
    qtbot: QtBot, window: MainWindow
) -> None:
    """Ctrl+Z (undo) holds Ctrl down for an unrelated shortcut -- its
    eventual release must not also count as "tapped alone."."""
    session = window.session
    assert session is not None
    window._on_tag_create("vacation")
    assert len(session.tags.list_all()) == 1

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyPress(window.result_list, Qt.Key.Key_Control)
    qtbot.keyPress(window.result_list, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyRelease(window.result_list, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyRelease(window.result_list, Qt.Key.Key_Control)

    assert session.tags.list_all() == []  # the undo itself still fired
    assert window._tag_shortcut_mode_action.isChecked() is False


def test_selected_tag_mode_numbers_and_toggles_checked_tags_instead(
    qtbot: QtBot, window: MainWindow
) -> None:
    session = window.session
    assert session is not None
    current_id = session.state.result_set[0]
    session.state.current_item = current_id
    window._on_tag_create("a")
    window._on_tag_create("b")
    tag_a = session.tags.list_all()[0]
    window._on_item_tag_toggle(tag_a.id)  # "a" is now checked on the current item

    window._toggle_tag_shortcut_mode()
    assert window._tag_shortcut_mode_action.isChecked() is True

    tag_id = window.item_tag_panel.model.tag_id_for_shortcut(1, selected=True)
    assert tag_id == tag_a.id

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyClick(window.result_list, Qt.Key.Key_1)

    assert session.mappings.tags_for_media(current_id) == []  # toggled back off
