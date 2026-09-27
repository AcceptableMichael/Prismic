from pytestqt.qtbot import QtBot

from prismic.ui.scan_progress_bar import ScanProgressBar


def test_reset_progress_defaults_to_the_later_scan_label(qtbot: QtBot) -> None:
    bar = ScanProgressBar()
    qtbot.addWidget(bar)

    bar.reset_progress()

    assert bar.format() == "Detecting any moved files"


def test_reset_progress_with_is_first_scan_shows_the_scanning_label(qtbot: QtBot) -> None:
    bar = ScanProgressBar()
    qtbot.addWidget(bar)

    bar.reset_progress(is_first_scan=True)

    assert bar.format() == "Scanning all files"


def test_the_label_does_not_change_as_progress_ticks_in(qtbot: QtBot) -> None:
    """The label reflects which *pass* this is, decided once up front --
    not re-derived per tick from `expected_total`, which would flicker if
    a brand-new collection's `expected_total` (0) were confused with an
    ordinary rescan of a genuinely empty one."""
    bar = ScanProgressBar()
    qtbot.addWidget(bar)
    bar.reset_progress(is_first_scan=True)

    bar.report_progress(3, 0)
    qtbot.waitUntil(lambda: bar.value() == 3, timeout=1000)

    assert bar.format() == "Scanning all files"
