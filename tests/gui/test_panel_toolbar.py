"""The shuffle/full-screen toolbar row above the item-tags panel."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from prismic.application.input import shortcuts
from prismic.domain.media import Media, MediaState
from prismic.ui.main_window import MainWindow


@pytest.fixture
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    return win


@pytest.fixture
def open_window(qtbot: QtBot, window: MainWindow, collection_dir: Path) -> MainWindow:
    window.open_collection(collection_dir)
    qtbot.waitUntil(lambda: window.result_model.rowCount() == 2, timeout=5000)
    return window


def _media(media_id: int, path: str) -> Media:
    return Media(
        id=media_id,
        relative_path=path,
        content_hash="",
        size=0,
        mtime=0.0,
        state=MediaState.ACTIVE,
    )


# -- The row itself -----------------------------------------------------------


def test_the_toolbar_has_a_shuffle_and_a_fullscreen_button(window: MainWindow) -> None:
    assert window.panel_toolbar.shuffle_button.isCheckable()
    assert window.panel_toolbar.fullscreen_button.isCheckable()
    assert not window.panel_toolbar.shuffle_button.isChecked()
    assert not window.panel_toolbar.fullscreen_button.isChecked()


def test_the_toolbar_matches_the_panel_titles_own_height(window: MainWindow) -> None:
    """ "The same height as the box containing the label 'Edit this
    file'" -- queried from that label directly rather than a hard-coded
    guess at it, so a font/padding change to one keeps the other in
    step."""
    assert window.panel_toolbar.height() == window.item_tag_panel.title_label.sizeHint().height()


def test_focus_mode_hides_the_toolbar_too(qtbot: QtBot, window: MainWindow) -> None:
    """Focus Mode hides `_left_column` as a whole, not `_tag_splitter`
    directly -- the toolbar sits in that same column, above the
    splitter, and should disappear right along with it."""
    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)

    qtbot.keyClick(window.result_list, Qt.Key.Key_Space)

    assert window.panel_toolbar.isVisible() is False


# -- _reordered_by_shuffle, in isolation ---------------------------------------
# No session or collection needed -- the method only ever touches
# `self._shuffled_order`.


def test_a_fresh_shuffle_list_contains_every_id_exactly_once(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each new id is spliced in at a random position relative to what's
    already placed -- with nothing placed yet, that's still a genuine
    random choice per insertion (not necessarily arrival order), so this
    only pins membership, not a specific arrangement. `random.randint` is
    pinned to "always append" here purely to make the assertion
    deterministic to write, not because that's the only order this could
    produce."""
    monkeypatch.setattr("random.randint", lambda _lo, hi: hi)
    media = [_media(1, "a"), _media(2, "b"), _media(3, "c")]

    reordered = window._reordered_by_shuffle(media)

    assert {m.id for m in reordered} == {1, 2, 3}
    assert window._shuffled_order == [1, 2, 3]


def test_an_established_order_is_not_reshuffled_on_a_later_call(window: MainWindow) -> None:
    media = [_media(1, "a"), _media(2, "b"), _media(3, "c")]
    window._shuffled_order = [3, 1, 2]  # some arrangement from an earlier shuffle

    reordered = window._reordered_by_shuffle(media)

    assert [m.id for m in reordered] == [3, 1, 2]


def test_an_item_that_is_no_longer_eligible_is_dropped(window: MainWindow) -> None:
    window._shuffled_order = [3, 1, 2]

    reordered = window._reordered_by_shuffle([_media(1, "a"), _media(2, "b")])  # 3 is gone

    assert [m.id for m in reordered] == [1, 2]
    assert window._shuffled_order == [1, 2]


def test_a_newly_eligible_item_is_spliced_in_at_a_random_position(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    window._shuffled_order = [1, 2]
    monkeypatch.setattr("random.randint", lambda _lo, _hi: 1)  # deterministic: the middle

    reordered = window._reordered_by_shuffle([_media(1, "a"), _media(2, "b"), _media(3, "c")])

    assert [m.id for m in reordered] == [1, 3, 2]


# -- Shuffle, through the real button ------------------------------------------


def test_toggling_shuffle_reorders_the_result_list(
    qtbot: QtBot, open_window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = open_window.session
    assert session is not None
    original_order = list(session.state.result_set)
    monkeypatch.setattr("random.shuffle", lambda seq: seq.reverse())

    qtbot.mouseClick(open_window.panel_toolbar.shuffle_button, Qt.MouseButton.LeftButton)

    assert open_window._display_order == list(reversed(original_order))
    assert open_window.result_model.media_at(0).id == original_order[-1]


def test_the_shuffled_arrangement_survives_an_unrelated_refresh(
    qtbot: QtBot, open_window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tagging a file re-triggers `_refresh_all()`, which re-runs the
    shuffle logic -- it must reapply the existing arrangement, not draw a
    brand-new random one on every unrelated change."""
    monkeypatch.setattr("random.shuffle", lambda seq: seq.reverse())
    qtbot.mouseClick(open_window.panel_toolbar.shuffle_button, Qt.MouseButton.LeftButton)
    shuffled_order = list(open_window._display_order)

    open_window._on_tag_create("vacation")

    assert open_window._display_order == shuffled_order


def test_toggling_shuffle_off_restores_the_natural_order(
    qtbot: QtBot, open_window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = open_window.session
    assert session is not None
    original_order = list(session.state.result_set)
    monkeypatch.setattr("random.shuffle", lambda seq: seq.reverse())
    qtbot.mouseClick(open_window.panel_toolbar.shuffle_button, Qt.MouseButton.LeftButton)

    qtbot.mouseClick(open_window.panel_toolbar.shuffle_button, Qt.MouseButton.LeftButton)

    assert open_window._display_order == original_order


def test_turning_shuffle_on_again_draws_a_fresh_order_not_the_old_one(
    qtbot: QtBot, open_window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[int]] = []

    def fake_shuffle(seq: list[int]) -> None:
        calls.append(list(seq))
        seq.reverse()

    monkeypatch.setattr("random.shuffle", fake_shuffle)

    qtbot.mouseClick(open_window.panel_toolbar.shuffle_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(open_window.panel_toolbar.shuffle_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(open_window.panel_toolbar.shuffle_button, Qt.MouseButton.LeftButton)

    assert len(calls) == 2  # once per turning-on, not on the turning-off in between


def test_navigation_follows_the_shuffled_order(
    qtbot: QtBot, open_window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = open_window.session
    assert session is not None
    monkeypatch.setattr("random.shuffle", lambda seq: seq.reverse())
    qtbot.mouseClick(open_window.panel_toolbar.shuffle_button, Qt.MouseButton.LeftButton)
    shuffled_first, shuffled_second = open_window._display_order
    session.state.current_item = shuffled_first
    open_window._sync_result_selection()

    qtbot.keyClick(open_window.result_list, Qt.Key.Key_Right)

    assert session.state.current_item == shuffled_second


# -- True full screen -----------------------------------------------------------


def test_toggling_fullscreen_enters_real_fullscreen(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.mouseClick(window.panel_toolbar.fullscreen_button, Qt.MouseButton.LeftButton)

    assert window.isFullScreen()


def test_toggling_fullscreen_off_leaves_it(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.mouseClick(window.panel_toolbar.fullscreen_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(window.panel_toolbar.fullscreen_button, Qt.MouseButton.LeftButton)

    assert not window.isFullScreen()


def test_leaving_fullscreen_restores_a_maximized_window_to_maximized(
    qtbot: QtBot, window: MainWindow
) -> None:
    """`showFullScreen()` then `showNormal()` alone drops back to plain
    windowed, silently un-maximizing a window that was maximized before
    -- not "restore ... to the size it was before" when "before" was
    maximized. `_pre_fullscreen_state` is what closes that gap."""
    window.showMaximized()
    qtbot.waitUntil(lambda: window.isMaximized(), timeout=1000)

    qtbot.mouseClick(window.panel_toolbar.fullscreen_button, Qt.MouseButton.LeftButton)
    assert window.isFullScreen()

    qtbot.mouseClick(window.panel_toolbar.fullscreen_button, Qt.MouseButton.LeftButton)

    assert not window.isFullScreen()
    assert window.isMaximized()


def test_leaving_fullscreen_restores_a_normal_window_to_its_own_geometry(
    qtbot: QtBot, window: MainWindow
) -> None:
    window.showNormal()
    qtbot.waitUntil(lambda: not window.isMaximized() and not window.isFullScreen(), timeout=1000)
    window.setGeometry(50, 60, 700, 500)
    original_geometry = window.geometry()

    qtbot.mouseClick(window.panel_toolbar.fullscreen_button, Qt.MouseButton.LeftButton)
    assert window.isFullScreen()

    qtbot.mouseClick(window.panel_toolbar.fullscreen_button, Qt.MouseButton.LeftButton)

    assert not window.isFullScreen()
    assert not window.isMaximized()
    assert window.geometry() == original_geometry


def test_any_key_exits_fullscreen(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.mouseClick(window.panel_toolbar.fullscreen_button, Qt.MouseButton.LeftButton)
    assert window.isFullScreen()

    qtbot.keyClick(window, Qt.Key.Key_A)

    assert not window.isFullScreen()
    assert not window.panel_toolbar.fullscreen_button.isChecked()


def test_any_click_exits_fullscreen(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.mouseClick(window.panel_toolbar.fullscreen_button, Qt.MouseButton.LeftButton)
    assert window.isFullScreen()

    qtbot.mouseClick(window.item_tag_panel.header, Qt.MouseButton.LeftButton)

    assert not window.isFullScreen()


def test_the_exiting_click_does_nothing_else(qtbot: QtBot, window: MainWindow) -> None:
    """The whole point of "any key or click" is that it's swallowed
    entirely -- a click that would otherwise have toggled shuffle just
    exits full screen instead, on the first click. A second click is a
    perfectly ordinary one again."""
    qtbot.mouseClick(window.panel_toolbar.fullscreen_button, Qt.MouseButton.LeftButton)
    assert window.isFullScreen()

    qtbot.mouseClick(window.panel_toolbar.shuffle_button, Qt.MouseButton.LeftButton)

    assert not window.isFullScreen()
    assert not window.panel_toolbar.shuffle_button.isChecked()

    qtbot.mouseClick(window.panel_toolbar.shuffle_button, Qt.MouseButton.LeftButton)

    assert window.panel_toolbar.shuffle_button.isChecked()


# -- Keyboard shortcuts -------------------------------------------------------
# Both buttons are plain QToolButtons with no QAction behind them, so
# these go through KeyboardController's generic dispatch rather than a
# QAction's own QShortcut -- worth covering directly rather than trusting
# the wiring by inspection.


def test_shuffle_shortcut_fires_once_rebound_off_its_colliding_default(
    qtbot: QtBot, open_window: MainWindow
) -> None:
    """Shuffle's own default (Ctrl+R) collides with Rescan's, at the
    user's explicit request -- and Rescan, a real `QAction` with its own
    `QShortcut`, wins that particular key outright by default, since only
    one shortcut can ever actually fire from a single keypress. That's
    exactly the conflict Settings reports rather than silently resolving
    (see `test_shortcuts.py::test_rescan_and_shuffle_share_ctrl_r_as_a_
    reported_conflict`) -- not a dispatch bug, and not this test's
    concern. What this test pins is that Shuffle's own wiring works once
    a user has actually rebound one of the two off Ctrl+R, which is what
    the conflict warning is there to prompt."""
    open_window.bindings.set_binding(shortcuts.SHUFFLE_RESULTS, "Ctrl+Shift+R")
    open_window._apply_bindings()
    open_window.result_list.setFocus()
    qtbot.waitUntil(lambda: open_window.result_list.hasFocus(), timeout=1000)

    qtbot.keyClick(
        open_window.result_list,
        Qt.Key.Key_R,
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
    )

    assert open_window.panel_toolbar.shuffle_button.isChecked()


def test_ctrl_r_by_default_rescans_rather_than_shuffling(
    qtbot: QtBot, open_window: MainWindow
) -> None:
    """The other half of the same story: out of the box, Ctrl+R is
    Rescan's key, not Shuffle's, even though Shuffle also claims it as a
    default -- confirms which of the two conflicting shortcuts actually
    wins the physical key before any rebinding happens."""
    open_window.result_list.setFocus()
    qtbot.waitUntil(lambda: open_window.result_list.hasFocus(), timeout=1000)

    qtbot.keyClick(open_window.result_list, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)

    assert not open_window.panel_toolbar.shuffle_button.isChecked()


def test_ctrl_f_toggles_fullscreen(qtbot: QtBot, open_window: MainWindow) -> None:
    open_window.result_list.setFocus()
    qtbot.waitUntil(lambda: open_window.result_list.hasFocus(), timeout=1000)

    qtbot.keyClick(open_window.result_list, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)

    assert open_window.panel_toolbar.fullscreen_button.isChecked()
    assert open_window.isFullScreen()
