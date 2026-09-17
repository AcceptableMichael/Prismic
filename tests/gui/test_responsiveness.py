"""Responsiveness under rapid interaction, per Phase 6.

The viewer's image decode is synchronous today (see the Phase 5 phase file
note on why `ImageLoader`'s generation-staleness machinery isn't wired in
yet), so there's no genuine async race to provoke here with small test
fixtures -- what these tests actually guard against is a rapid burst of
input corrupting `ApplicationState` or crashing the UI outright.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from prismic.ui.main_window import MainWindow

_FILE_COUNT = 20


def _make_collection(tmp_path: Path) -> Path:
    root = tmp_path / "vacation"
    root.mkdir()
    for index in range(_FILE_COUNT):
        (root / f"photo_{index:03d}.jpg").write_bytes(f"content-{index}".encode())
    return root


def test_rapid_navigation_lands_on_a_consistent_final_state(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.open_collection(_make_collection(tmp_path))
    qtbot.waitUntil(lambda: window.result_model.rowCount() == _FILE_COUNT, timeout=5000)

    window.result_list.setFocus()
    qtbot.waitUntil(lambda: window.result_list.hasFocus(), timeout=1000)

    for _ in range(_FILE_COUNT + 10):  # deliberately overshoot past the last item
        qtbot.keyClick(window.result_list, Qt.Key.Key_Right)

    session = window.session
    assert session is not None
    assert session.state.current_item == session.state.result_set[-1]
    assert window.viewer.current_path is not None


def test_rapid_filter_toggling_leaves_a_consistent_result_set(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_collection(_make_collection(tmp_path))
    qtbot.waitUntil(lambda: window.result_model.rowCount() == _FILE_COUNT, timeout=5000)

    window._on_tag_create("beach")
    tag = window.session.tags.list_all()[0]  # type: ignore[union-attr]

    for _ in range(25):
        window._on_filter_toggle(tag.id)  # select
        window._on_filter_toggle(tag.id)  # deselect

    # Untagged, so an even number of toggles must land back at "all media".
    assert window.result_model.rowCount() == _FILE_COUNT
    assert window.session.state.selected_tag_ids == []  # type: ignore[union-attr]
