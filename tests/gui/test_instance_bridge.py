"""Focus-forwarding when a second launch targets an already-open
collection, per the user's explicit request after Phase 6: rather than
just showing an error, ask the existing instance to raise its window.
"""

from pathlib import Path

from pytestqt.qtbot import QtBot

from prismic.ui.instance_bridge import InstanceBridge, request_focus
from prismic.ui.main_window import MainWindow


def test_request_focus_with_no_listener_returns_false(tmp_path: Path) -> None:
    assert request_focus(tmp_path / "nothing.prismic") is False


def test_instance_bridge_delivers_a_raise_request(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = tmp_path / "vacation.prismic"
    database_path.touch()

    bridge = InstanceBridge()
    bridge.take_ownership(database_path)
    try:
        received = []
        bridge.raise_requested.connect(lambda: received.append(True))

        delivered = request_focus(database_path)

        assert delivered is True
        qtbot.waitUntil(lambda: received == [True], timeout=2000)
    finally:
        bridge.release()


def test_opening_the_same_collection_twice_focuses_the_first_window_instead_of_erroring(
    qtbot: QtBot, collection_dir: Path
) -> None:
    first = MainWindow()
    qtbot.addWidget(first)
    first.open_collection(collection_dir)
    qtbot.waitUntil(lambda: first.session is not None, timeout=5000)
    assert first._instance_bridge is not None

    second = MainWindow()
    qtbot.addWidget(second)

    with qtbot.waitSignal(first._instance_bridge.raise_requested, timeout=2000):
        second.open_collection(collection_dir)  # not is_startup: a manual "File > Open"

    assert second.session is None  # the second window never actually opened it


def test_a_locked_startup_launch_closes_itself_after_focusing_the_first(
    qtbot: QtBot, collection_dir: Path
) -> None:
    first = MainWindow()
    qtbot.addWidget(first)
    first.open_collection(collection_dir)
    qtbot.waitUntil(lambda: first.session is not None, timeout=5000)

    second = MainWindow()
    qtbot.addWidget(second)
    second.show()

    second.open_collection(collection_dir, is_startup=True)

    qtbot.waitUntil(lambda: not second.isVisible(), timeout=2000)
    assert second.session is None
