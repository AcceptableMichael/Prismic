"""Application startup: constructs the QApplication and top-level window."""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from prismic.ui.main_window import MainWindow

# Qt Multimedia's "windows" (Media Foundation) backend has no VP8/VP9/Opus/
# Vorbis decoders, so it can't play WebM at all -- a required format per the
# overview. Its "ffmpeg" backend does, verified by actually playing the
# fixtures in tests/fixtures/media/, not by trusting QMediaFormat's static
# capability query (which claims WebM/VP9 are unsupported even when they
# work fine in practice). This build's default already happens to be
# "ffmpeg", but that's pinned explicitly rather than relied on implicitly,
# since a required feature shouldn't depend on an undocumented default that
# could change. Must be set before any QtMultimedia object is constructed.
os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")


def run(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
