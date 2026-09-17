"""The media viewer: an image view with zoom/pan, or a video player with
play/pause/seek controls, switching between the two based on the current
item's extension. Navigation between items happens without leaving the
viewer — `show_media()` just swaps what's displayed in place.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from prismic.media.formats import SUPPORTED_VIDEO_EXTENSIONS
from prismic.media.image import ImageLoadError, load_image
from prismic.media.video import VideoPlayer
from prismic.ui.image_view import ImageView


class MediaViewer(QWidget):
    load_error = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._image_view = ImageView()
        self._video_widget = QVideoWidget()
        self._video_player = VideoPlayer(self)
        self._video_player.qt_player.setVideoOutput(self._video_widget)
        self._video_player.load_failed.connect(self.load_error)
        self._video_player.qt_player.positionChanged.connect(self._on_position_changed)
        self._video_player.qt_player.durationChanged.connect(self._on_duration_changed)
        self._video_player.qt_player.playbackStateChanged.connect(self._on_playback_state_changed)

        self._empty_label = QLabel("No collection open")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._empty_label)
        self._stack.addWidget(self._image_view)
        self._stack.addWidget(self._video_widget)

        self._play_pause_button = QPushButton("Play")
        self._play_pause_button.clicked.connect(self.toggle_playback)
        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 0)
        self._seek_slider.sliderMoved.connect(self._video_player.seek)

        self._controls = QWidget()
        controls_layout = QHBoxLayout(self._controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.addWidget(self._play_pause_button)
        controls_layout.addWidget(self._seek_slider)
        self._controls.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self._stack)
        layout.addWidget(self._controls)

        self._current_path: Path | None = None

    def show_media(self, path: Path) -> None:
        self._current_path = path
        if path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
            self._show_video(path)
        else:
            self._show_image(path)

    def clear(self) -> None:
        self._current_path = None
        self._video_player.stop()
        self._image_view.clear()
        self._controls.setVisible(False)
        self._stack.setCurrentWidget(self._empty_label)

    def _show_image(self, path: Path) -> None:
        self._video_player.stop()
        self._controls.setVisible(False)
        outcome = load_image(path)
        if isinstance(outcome, ImageLoadError):
            self.load_error.emit(outcome.reason)
            self._stack.setCurrentWidget(self._empty_label)
            return
        self._image_view.set_image(outcome)
        self._stack.setCurrentWidget(self._image_view)

    def _show_video(self, path: Path) -> None:
        self._image_view.clear()
        self._controls.setVisible(True)
        self._video_player.load(path)
        self._stack.setCurrentWidget(self._video_widget)

    def toggle_playback(self) -> None:
        if self._video_player.playback_state == QMediaPlayer.PlaybackState.PlayingState:
            self._video_player.pause()
        else:
            self._video_player.play()

    def _on_position_changed(self, position: int) -> None:
        if not self._seek_slider.isSliderDown():
            self._seek_slider.setValue(position)

    def _on_duration_changed(self, duration: int) -> None:
        self._seek_slider.setRange(0, duration)

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._play_pause_button.setText("Pause" if is_playing else "Play")

    @property
    def image_view(self) -> ImageView:
        return self._image_view

    @property
    def video_player(self) -> VideoPlayer:
        return self._video_player

    @property
    def current_path(self) -> Path | None:
        return self._current_path

    @property
    def is_showing_video(self) -> bool:
        return self._stack.currentWidget() is self._video_widget

    @property
    def is_showing_image(self) -> bool:
        return self._stack.currentWidget() is self._image_view
