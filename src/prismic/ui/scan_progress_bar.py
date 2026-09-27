"""A fixed-width indicator in the status bar's permanent (right-hand) region,
shown for the duration of a background scan/hash/reconcile pass.

Sits alongside `TransientMessageBar` in the same permanent area, opposite
`HoverExplainerBar` -- see `MainWindow._build_status_bar`. Purely
presentational: `MainWindow` shows it when it starts watching a
reconciliation future, hides it once that future completes, and feeds it
progress via `report_progress()` in between.

The label itself reflects whether the collection has ever been scanned
before -- see `reset_progress(is_first_scan=...)`, fed from
`PrismicSession.is_first_scan`. A brand-new root has nothing to compare
against yet (there's no "moved" or "changed" to detect relative to a
previous pass), so it reads "Scanning all files" instead of the usual
"Detecting any moved files".
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QProgressBar, QWidget

_FIRST_SCAN_FORMAT = "Scanning all files"
_LATER_SCAN_FORMAT = "Detecting any moved files"


class ScanProgressBar(QProgressBar):
    # `report_progress()` is called from whichever thread is running the
    # scan (see `application.session.PrismicSession.rescan`), never the GUI
    # thread. Routing it through a signal -- rather than calling setRange()/
    # setValue() directly -- is what makes that safe: emitting from a
    # different thread than the receiving QObject's own is automatically a
    # queued connection, the same marshaling `FutureWatcher` relies on for
    # a future's completion.
    _progress = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("scanProgressBar")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setTextVisible(True)
        self.setFixedWidth(300)
        self._progress.connect(self._apply_progress)
        self.reset_progress(is_first_scan=False)
        self.hide()

    def report_progress(self, processed: int, expected_total: int) -> None:
        self._progress.emit(processed, expected_total)

    def reset_progress(self, *, is_first_scan: bool = False) -> None:
        # No count yet (the very first scan of a collection, before any
        # scan has completed to leave a total behind) -- min == max == 0 is
        # Qt's own convention for an indeterminate/busy progress bar, so
        # this falls back to that rather than a misleading "0 of 0" full bar.
        self.setFormat(_FIRST_SCAN_FORMAT if is_first_scan else _LATER_SCAN_FORMAT)
        self.setRange(0, 0)
        self.setValue(0)

    def _apply_progress(self, processed: int, expected_total: int) -> None:
        # `expected_total` is last scan's count, so a collection that grew
        # since then can push `processed` past it -- widen the denominator
        # rather than let the bar report over 100%, or (when last scan's
        # count was 0, e.g. a brand new collection) stay stuck indeterminate
        # forever despite files actually being counted this pass.
        total = max(expected_total, processed)
        self.setRange(0, total)
        self.setValue(processed)
