from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QDialog
from pytestqt.qtbot import QtBot

from prismic.application.input import shortcuts
from prismic.ui.main_window import MainWindow
from prismic.ui.settings_dialog import SettingsDialog


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
    tag_id = window.item_tag_panel.model.tag_id_for_slot(0, selected=False)
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
    tag_id = window.item_tag_panel.model.tag_id_for_slot(0, selected=False)
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

    tag_id = window.item_tag_panel.model.tag_id_for_slot(0, selected=True)
    assert tag_id == tag_a.id

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyClick(window.result_list, Qt.Key.Key_1)

    assert session.mappings.tags_for_media(current_id) == []  # toggled back off


# -- Configurable bindings ---------------------------------------------------
# Every key above is a *default*, not a constant. These check that
# rebinding one in Settings actually moves the behavior with it, rather
# than the new key being recorded and then ignored.


def rebind(window: MainWindow, shortcut_id: str, binding: str) -> None:
    """Do what the Settings dialog does: change a binding, then tell the
    window to re-apply. `MainWindow.open_settings` wires exactly this pair
    together via the dialog's `bindings_changed` signal."""
    window.bindings.set_binding(shortcut_id, binding)
    window._apply_bindings()


def test_rebinding_navigation_moves_it_to_the_new_key(qtbot: QtBot, window: MainWindow) -> None:
    session = window.session
    assert session is not None
    first_id, second_id = session.state.result_set
    session.state.current_item = first_id
    window._sync_result_selection()
    rebind(window, shortcuts.NAVIGATE_NEXT, "F5")

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyClick(window.result_list, Qt.Key.Key_F5)

    assert session.state.current_item == second_id

    # ...and off the old one, rather than answering to both.
    session.state.current_item = first_id
    qtbot.keyClick(window.result_list, Qt.Key.Key_Right)

    assert session.state.current_item == first_id


def test_an_unbound_shortcut_stops_responding(qtbot: QtBot, window: MainWindow) -> None:
    rebind(window, shortcuts.FOCUS_MODE, "")

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyClick(window.result_list, Qt.Key.Key_Space)

    assert window._focus_mode_action.isChecked() is False


def test_escape_still_leaves_focus_mode_when_dismiss_is_unbound(
    qtbot: QtBot, window: MainWindow
) -> None:
    """A deliberate safety hatch: focus mode hides the menu bar, so a user
    who clears both Dismiss and Focus Mode would otherwise be stuck in it
    with no way back short of quitting."""
    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyClick(window.result_list, Qt.Key.Key_Space)
    assert window._focus_mode_action.isChecked() is True
    rebind(window, shortcuts.DISMISS, "")

    qtbot.keyClick(window.result_list, Qt.Key.Key_Escape)

    assert window._focus_mode_action.isChecked() is False


def test_rebinding_dismiss_moves_it_off_escape(qtbot: QtBot, window: MainWindow) -> None:
    rebind(window, shortcuts.DISMISS, "F4")
    window.item_tag_panel.search_box.setFocus()
    qtbot.waitUntil(lambda: window.item_tag_panel.search_box.hasFocus(), timeout=1000)

    qtbot.keyClick(window.item_tag_panel.search_box, Qt.Key.Key_F4)

    assert window.result_list.hasFocus()


def test_rebinding_the_tag_search_cycle_moves_the_whole_cycle(
    qtbot: QtBot, window: MainWindow
) -> None:
    rebind(window, shortcuts.FOCUS_TAG_SEARCH, "F2")
    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)

    qtbot.keyClick(window.result_list, Qt.Key.Key_F2)
    assert window.item_tag_panel.search_box.hasFocus()

    qtbot.keyClick(window.item_tag_panel.search_box, Qt.Key.Key_F2)
    assert window.filter_panel.search_box.hasFocus()

    qtbot.keyClick(window.filter_panel.search_box, Qt.Key.Key_F2)
    assert window.result_list.hasFocus()


def test_rebinding_a_menu_shortcut_updates_the_action(window: MainWindow) -> None:
    rebind(window, shortcuts.RESCAN, "F5")

    assert window._shortcut_actions[shortcuts.RESCAN].shortcut() == QKeySequence("F5")


def test_unbinding_a_menu_shortcut_leaves_the_action_with_no_key(window: MainWindow) -> None:
    rebind(window, shortcuts.RESCAN, "")

    assert window._shortcut_actions[shortcuts.RESCAN].shortcut().isEmpty()


def test_the_focus_mode_menu_entry_shows_its_current_key(window: MainWindow) -> None:
    """It has no QShortcut of its own -- one would go ambiguous against
    the viewer's play/pause button -- so its key is menu text instead,
    which still has to follow a rebind rather than keep advertising
    Space."""
    rebind(window, shortcuts.FOCUS_MODE, "F9")

    assert window._focus_mode_action.text() == "Focus Mode\tF9"

    rebind(window, shortcuts.FOCUS_MODE, "")

    assert window._focus_mode_action.text() == "Focus Mode"


def test_rebinding_play_pause_moves_the_viewer_button_shortcut(window: MainWindow) -> None:
    rebind(window, shortcuts.VIEWER_PLAY_PAUSE, "F10")

    assert window.viewer.play_pause_button.shortcut() == QKeySequence("F10")


def test_rebinding_a_quick_select_key_toggles_the_same_tag(
    qtbot: QtBot, window: MainWindow
) -> None:
    session = window.session
    assert session is not None
    current_id = session.state.result_set[0]
    session.state.current_item = current_id
    window._on_tag_create("a")
    tag_id = window.item_tag_panel.model.tag_id_for_slot(0, selected=False)
    assert tag_id is not None
    rebind(window, shortcuts.quick_select_id(0), "Q")

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyClick(window.result_list, Qt.Key.Key_Q)

    assert [t.id for t in session.mappings.tags_for_media(current_id)] == [tag_id]

    # ...and the digit it used to be on is genuinely free again, not
    # still quietly wired up alongside the new key.
    qtbot.keyClick(window.result_list, Qt.Key.Key_1)

    assert [t.id for t in session.mappings.tags_for_media(current_id)] == [tag_id]


def test_a_rebound_quick_select_key_is_still_typeable_with_ctrl(
    qtbot: QtBot, window: MainWindow
) -> None:
    """The escape hatch generalizes past digits: whatever key a
    quick-select shortcut is spent on, Ctrl+it types that character."""
    session = window.session
    assert session is not None
    session.state.current_item = session.state.result_set[0]
    window._on_tag_create("a")
    rebind(window, shortcuts.quick_select_id(0), "Q")

    window.item_tag_panel.search_box.setFocus()
    qtbot.waitUntil(lambda: window.item_tag_panel.search_box.hasFocus(), timeout=1000)
    qtbot.keyClick(
        window.item_tag_panel.search_box, Qt.Key.Key_Q, Qt.KeyboardModifier.ControlModifier
    )

    assert window.item_tag_panel.search_box.text() == "q"
    assert session.mappings.tags_for_media(session.state.current_item) == []


def test_the_tag_rows_label_whichever_key_is_bound(window: MainWindow) -> None:
    window._on_tag_create("a")
    assert window._quick_select_labels()[0] == "1"

    rebind(window, shortcuts.quick_select_id(0), "Ctrl+Q")

    # The last key of the combination -- the checkbox has no room for the
    # whole thing, and "Q" is the part that identifies it.
    assert window._quick_select_labels()[0] == "Q"

    rebind(window, shortcuts.quick_select_id(0), "")

    assert 0 not in window._quick_select_labels()


def test_rebinding_the_numbering_swap_moves_it_to_another_modifier(
    qtbot: QtBot, window: MainWindow
) -> None:
    rebind(window, shortcuts.SWAP_TAG_NUMBERING, "Alt")
    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)

    qtbot.keyPress(window.result_list, Qt.Key.Key_Alt)
    qtbot.keyRelease(window.result_list, Qt.Key.Key_Alt)

    assert window._tag_shortcut_mode_action.isChecked() is True

    # Ctrl is an ordinary modifier again, with no gesture attached.
    qtbot.keyPress(window.result_list, Qt.Key.Key_Control)
    qtbot.keyRelease(window.result_list, Qt.Key.Key_Control)

    assert window._tag_shortcut_mode_action.isChecked() is True


def test_unbinding_the_numbering_swap_disables_the_gesture(
    qtbot: QtBot, window: MainWindow
) -> None:
    rebind(window, shortcuts.SWAP_TAG_NUMBERING, "")
    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)

    qtbot.keyPress(window.result_list, Qt.Key.Key_Control)
    qtbot.keyRelease(window.result_list, Qt.Key.Key_Control)

    assert window._tag_shortcut_mode_action.isChecked() is False


def test_the_numbering_swap_works_on_an_ordinary_key_too(qtbot: QtBot, window: MainWindow) -> None:
    """It's a regular input now -- bound to something that isn't a
    modifier, it fires on the press like any other shortcut rather than
    needing a tap-and-release."""
    rebind(window, shortcuts.SWAP_TAG_NUMBERING, "F8")
    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)

    qtbot.keyClick(window.result_list, Qt.Key.Key_F8)

    assert window._tag_shortcut_mode_action.isChecked() is True

    qtbot.keyClick(window.result_list, Qt.Key.Key_F8)

    assert window._tag_shortcut_mode_action.isChecked() is False


def test_any_shortcut_can_be_bound_to_a_modifier_tap(qtbot: QtBot, window: MainWindow) -> None:
    """Nothing singles out which commands accept the tap gesture -- the
    capture box takes one for every row, so dispatch has to honour it
    for every command, or binding one would silently do nothing."""
    session = window.session
    assert session is not None
    first_id, second_id = session.state.result_set
    session.state.current_item = first_id
    window._sync_result_selection()
    rebind(window, shortcuts.SWAP_TAG_NUMBERING, "")  # free Ctrl up first
    rebind(window, shortcuts.NAVIGATE_NEXT, "Ctrl")

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyPress(window.result_list, Qt.Key.Key_Control)
    qtbot.keyRelease(window.result_list, Qt.Key.Key_Control)

    assert session.state.current_item == second_id


def test_a_menu_command_can_be_bound_to_a_modifier_tap(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Menu commands run as QActions rather than through the keyboard
    controller, so the tap dispatcher has to reach those too."""
    opened: list[SettingsDialog] = []

    def capture(dialog: SettingsDialog) -> int:
        opened.append(dialog)
        return 0

    monkeypatch.setattr(SettingsDialog, "exec", capture)
    rebind(window, shortcuts.SWAP_TAG_NUMBERING, "")
    rebind(window, shortcuts.OPEN_SETTINGS, "Ctrl")

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyPress(window.result_list, Qt.Key.Key_Control)
    qtbot.keyRelease(window.result_list, Qt.Key.Key_Control)

    assert len(opened) == 1


def test_a_quick_select_shortcut_can_be_bound_to_a_modifier_tap(
    qtbot: QtBot, window: MainWindow
) -> None:
    session = window.session
    assert session is not None
    current_id = session.state.result_set[0]
    session.state.current_item = current_id
    window._on_tag_create("a")
    tag_id = window.item_tag_panel.model.tag_id_for_slot(0, selected=False)
    assert tag_id is not None
    rebind(window, shortcuts.SWAP_TAG_NUMBERING, "")
    rebind(window, shortcuts.quick_select_id(0), "Ctrl")

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyPress(window.result_list, Qt.Key.Key_Control)
    qtbot.keyRelease(window.result_list, Qt.Key.Key_Control)

    assert [t.id for t in session.mappings.tags_for_media(current_id)] == [tag_id]


def test_shortcuts_stand_down_while_a_modal_dialog_is_open(
    qtbot: QtBot, window: MainWindow
) -> None:
    """Otherwise a keystroke meant for the Settings window's capture box
    would also fire whatever command it's currently bound to."""
    session = window.session
    assert session is not None
    first_id = session.state.result_set[0]
    session.state.current_item = first_id
    window._sync_result_selection()

    blocker = QDialog(window)
    blocker.setWindowModality(Qt.WindowModality.ApplicationModal)
    qtbot.addWidget(blocker)
    blocker.show()
    qtbot.waitExposed(blocker)
    qtbot.waitUntil(lambda: QApplication.activeModalWidget() is blocker, timeout=1000)

    qtbot.keyClick(blocker, Qt.Key.Key_Right)

    assert session.state.current_item == first_id

    blocker.close()
    qtbot.waitUntil(lambda: QApplication.activeModalWidget() is None, timeout=1000)
    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)
    qtbot.keyClick(window.result_list, Qt.Key.Key_Right)

    assert session.state.current_item != first_id  # working again afterwards


def test_opening_settings_applies_what_is_changed_in_it(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The connection between the two halves of the feature. Every other
    test here calls `_apply_bindings()` by hand; this is the one that
    checks `open_settings` actually subscribes to the dialog, rather than
    recording a rebind that never reaches the running UI. `exec()` is
    stubbed out because it would otherwise block on its own event loop."""
    opened: list[SettingsDialog] = []

    def capture(dialog: SettingsDialog) -> int:
        opened.append(dialog)
        return 0

    monkeypatch.setattr(SettingsDialog, "exec", capture)

    window.open_settings()

    assert len(opened) == 1
    row = next(r for r in opened[0].shortcuts_panel.rows if r.definition.id == shortcuts.RESCAN)
    qtbot.mouseClick(row._clear_button, Qt.MouseButton.LeftButton)

    assert window.bindings.binding(shortcuts.RESCAN) == ""
    assert window._shortcut_actions[shortcuts.RESCAN].shortcut().isEmpty()


def test_the_settings_menu_entry_opens_the_window(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[SettingsDialog] = []

    def capture(dialog: SettingsDialog) -> int:
        opened.append(dialog)
        return 0

    monkeypatch.setattr(SettingsDialog, "exec", capture)

    window._shortcut_actions[shortcuts.OPEN_SETTINGS].trigger()

    assert len(opened) == 1


def test_bindings_persist_across_windows(qtbot: QtBot) -> None:
    """A rebind is a preference, not session state -- it has to survive
    the app being closed and reopened."""
    first = MainWindow()
    qtbot.addWidget(first)
    first.bindings.set_binding(shortcuts.RESCAN, "F5")

    second = MainWindow()
    qtbot.addWidget(second)

    assert second.bindings.binding(shortcuts.RESCAN) == "F5"
    assert second._shortcut_actions[shortcuts.RESCAN].shortcut() == QKeySequence("F5")
