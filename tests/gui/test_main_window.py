import pytest
from pytestqt.qtbot import QtBot

from prismic.ui.main_window import MainWindow


@pytest.fixture
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    return win


def test_window_has_title(window: MainWindow) -> None:
    assert window.windowTitle() == "Prismic"


def test_shows_no_collection_placeholder(window: MainWindow) -> None:
    assert window.placeholder_label.text() == "No collection open"
