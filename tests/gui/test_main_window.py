import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from prismic.ui.main_window import MainWindow


@pytest.fixture
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    return win


def test_starts_with_no_keycaps(window: MainWindow) -> None:
    assert window.keycap_display.keycap_texts() == []


def test_typing_renders_one_keycap_per_character(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.keyClicks(window.text_input, "Hi!")

    assert window.keycap_display.keycap_texts() == ["H", "i", "!"]


def test_space_renders_as_visible_glyph(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.keyClicks(window.text_input, "a b")

    assert window.keycap_display.keycap_texts() == ["a", "␣", "b"]


def test_backspace_removes_the_last_keycap(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.keyClicks(window.text_input, "abc")
    qtbot.keyClick(window.text_input, Qt.Key.Key_Backspace)

    assert window.keycap_display.keycap_texts() == ["a", "b"]


def test_clearing_the_input_clears_all_keycaps(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.keyClicks(window.text_input, "abc")
    window.text_input.clear()

    assert window.keycap_display.keycap_texts() == []


def test_confirm_button_changes_background_color(qtbot: QtBot, window: MainWindow) -> None:
    before = window._central.styleSheet()

    qtbot.mouseClick(window.confirm_button, Qt.MouseButton.LeftButton)

    assert window._central.styleSheet() != before
