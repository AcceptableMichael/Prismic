from pathlib import Path

from PySide6.QtMultimedia import QMediaPlayer
from pytestqt.qtbot import QtBot

from prismic.ui.viewer import MediaViewer

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "media"


def test_shows_image_for_a_supported_image_path(qtbot: QtBot) -> None:
    viewer = MediaViewer()
    qtbot.addWidget(viewer)

    viewer.show_media(FIXTURES_DIR / "supported_image.png")

    assert viewer.is_showing_image is True
    assert viewer.is_showing_video is False


def test_shows_video_for_a_webm_path(qtbot: QtBot) -> None:
    viewer = MediaViewer()
    qtbot.addWidget(viewer)

    viewer.show_media(FIXTURES_DIR / "supported_video.webm")

    assert viewer.is_showing_video is True
    assert viewer.is_showing_image is False


def test_corrupt_image_emits_load_error_and_shows_nothing(qtbot: QtBot) -> None:
    viewer = MediaViewer()
    qtbot.addWidget(viewer)

    with qtbot.waitSignal(viewer.load_error, timeout=2000):
        viewer.show_media(FIXTURES_DIR / "corrupt_image.jpg")

    assert viewer.is_showing_image is False
    assert viewer.is_showing_video is False


def test_toggle_playback_starts_and_pauses_video(qtbot: QtBot) -> None:
    viewer = MediaViewer()
    qtbot.addWidget(viewer)
    viewer.show_media(FIXTURES_DIR / "supported_video.webm")
    qtbot.waitUntil(lambda: viewer.video_player.duration_ms > 0, timeout=5000)

    viewer.toggle_playback()
    qtbot.waitUntil(
        lambda: viewer.video_player.playback_state == QMediaPlayer.PlaybackState.PlayingState,
        timeout=5000,
    )

    viewer.toggle_playback()
    qtbot.waitUntil(
        lambda: viewer.video_player.playback_state != QMediaPlayer.PlaybackState.PlayingState,
        timeout=5000,
    )


def test_clear_resets_to_the_empty_state(qtbot: QtBot) -> None:
    viewer = MediaViewer()
    qtbot.addWidget(viewer)
    viewer.show_media(FIXTURES_DIR / "supported_image.png")

    viewer.clear()

    assert viewer.is_showing_image is False
    assert viewer.is_showing_video is False
    assert viewer.current_path is None
