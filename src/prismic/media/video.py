"""Video loading and playback via Qt Multimedia.

Requires the "ffmpeg" Qt Multimedia backend for WebM/VP9/Opus decoding —
see the comment in `bootstrap.py`, which sets `QT_MEDIA_BACKEND=ffmpeg`
before any multimedia object is constructed.

Unlike image decoding, video playback doesn't need its own generation-id
staleness suppression: `QMediaPlayer.setSource()` inherently supersedes
whatever it was previously loading at the Qt level (there's one player
object representing "the current video slot," not a pool of independent
async decode requests that could resolve out of order), so calling `load()`
again on the same `VideoPlayer` already discards the old one.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class VideoPlayer(QObject):
    """A single video's playback state: one player, one audio output.

    Owns its own `QAudioOutput` so audio-bearing video plays without the
    caller wiring one up separately. Load failures (corrupt/invalid/
    unsupported content) surface as a handled error via `load_failed`
    rather than a crash.
    """

    load_failed = Signal(str)  # human-readable reason

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._player.errorOccurred.connect(self._on_error)

    def load(self, path: Path) -> None:
        self._player.setSource(QUrl.fromLocalFile(str(path)))

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def seek(self, position_ms: int) -> None:
        self._player.setPosition(position_ms)

    @property
    def duration_ms(self) -> int:
        return self._player.duration()

    @property
    def position_ms(self) -> int:
        return self._player.position()

    @property
    def playback_state(self) -> QMediaPlayer.PlaybackState:
        return self._player.playbackState()

    @property
    def media_status(self) -> QMediaPlayer.MediaStatus:
        return self._player.mediaStatus()

    @property
    def qt_player(self) -> QMediaPlayer:
        """Escape hatch for signals this thin wrapper doesn't re-expose
        (e.g. `mediaStatusChanged`, `positionChanged`) — Phase 5 connects
        the viewer's UI directly to whatever it needs from here."""
        return self._player

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        self.load_failed.emit(error_string)
