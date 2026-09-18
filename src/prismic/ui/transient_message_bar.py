"""The right-hand region of the status bar: one-off transient messages
(chord-in-progress, "already open elsewhere", media load failures).

A small stand-in for `QStatusBar.showMessage()`, not a use of it: the
built-in version draws in the bar's normal (non-permanent) area, which is
where the hover-explainer lives here instead. Added as a *permanent*
status-bar widget so it keeps its own reserved space and is never hidden
by anything -- see `MainWindow._build_status_bar`.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QWidget


class TransientMessageBar(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("transientMessageBar")
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.clear)

    def show_message(self, text: str, timeout_ms: int = 0) -> None:
        self._timer.stop()
        self.setText(text)
        if timeout_ms > 0:
            self._timer.start(timeout_ms)
