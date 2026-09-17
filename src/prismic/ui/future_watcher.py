"""Marshals a `concurrent.futures.Future`'s completion back onto whichever
Qt thread owns this `QObject` (the GUI thread, in practice), via a queued
signal.

`Future.add_done_callback` runs its callback on whatever thread completed
the future — a background worker thread, for anything Phase 3's
`WorkerPool` dispatches. Emitting a Qt signal from there is still safe:
Qt's automatic connection type becomes a queued connection whenever the
emitting thread differs from the receiving `QObject`'s thread, which is
exactly the marshaling Phase 3's `PrismicSession.refresh_state()` docs
call for.
"""

from __future__ import annotations

from concurrent.futures import Future
from typing import Any

from PySide6.QtCore import QObject, Signal


class FutureWatcher(QObject):
    finished = Signal(object)  # the Future's result, once it's done

    def __init__(self, future: Future[Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        future.add_done_callback(self._on_done)

    def _on_done(self, future: Future[Any]) -> None:
        try:
            result = future.result()
        except Exception:
            return
        self.finished.emit(result)
