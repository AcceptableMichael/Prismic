from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from prismic.domain.tag import Tag
from prismic.ui.tag_panel import TagPanel

_TAGS = [Tag(id=1, name="kittens"), Tag(id=2, name="sunset"), Tag(id=3, name="sunrise")]


def _names(panel: TagPanel) -> list[str]:
    return [panel.model.tag_at(row).name for row in range(panel.model.rowCount())]


def test_checked_tags_are_sorted_to_the_top(qtbot: QtBot) -> None:
    panel = TagPanel("Item tags")
    qtbot.addWidget(panel)

    panel.set_tags(_TAGS, frozenset({2}))

    assert _names(panel) == ["sunset", "kittens", "sunrise"]


def test_search_narrows_only_the_unchecked_tags(qtbot: QtBot) -> None:
    panel = TagPanel("Item tags")
    qtbot.addWidget(panel)
    panel.set_tags(_TAGS, frozenset({2}))  # "sunset" checked

    panel.search_box.setText("sun")

    # "sunset" stays visible (checked, pinned) even though the query also
    # matches it; "sunrise" is the only *unchecked* match; "kittens" drops out.
    assert _names(panel) == ["sunset", "sunrise"]


def test_enter_with_a_match_toggles_the_top_filtered_result(qtbot: QtBot) -> None:
    panel = TagPanel("Item tags")
    qtbot.addWidget(panel)
    panel.set_tags(_TAGS, frozenset())
    toggled: list[int] = []
    panel.toggle_requested.connect(toggled.append)

    panel.search_box.setText("sun")
    qtbot.keyClick(panel.search_box, Qt.Key.Key_Return)

    assert toggled == [2]  # "sunset" sorts first among the matches
    assert panel.search_box.text() == ""


def test_enter_with_no_match_requests_create_and_check(qtbot: QtBot) -> None:
    panel = TagPanel("Item tags")
    qtbot.addWidget(panel)
    panel.set_tags(_TAGS, frozenset())
    created: list[str] = []
    panel.create_and_check_requested.connect(created.append)

    panel.search_box.setText("vacation")
    qtbot.keyClick(panel.search_box, Qt.Key.Key_Return)

    assert created == ["vacation"]
    assert panel.search_box.text() == ""


def test_enter_with_empty_search_does_nothing(qtbot: QtBot) -> None:
    panel = TagPanel("Item tags")
    qtbot.addWidget(panel)
    panel.set_tags(_TAGS, frozenset())
    toggled: list[int] = []
    created: list[str] = []
    panel.toggle_requested.connect(toggled.append)
    panel.create_and_check_requested.connect(created.append)

    qtbot.keyClick(panel.search_box, Qt.Key.Key_Return)

    assert toggled == []
    assert created == []


def test_focus_search_gives_the_search_box_focus(qtbot: QtBot) -> None:
    panel = TagPanel("Item tags")
    qtbot.addWidget(panel)
    panel.show()
    qtbot.waitExposed(panel)

    panel.focus_search()

    assert panel.search_box.hasFocus()
