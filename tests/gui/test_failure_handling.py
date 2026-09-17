"""Failure handling verified through the real UI, per Phase 6 -- not just
the Phase 1 persistence-layer unit tests for the same error types.
"""

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from prismic.application.session import PrismicSession
from prismic.persistence import database, migrations
from prismic.ui.main_window import MainWindow


@pytest.fixture
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    return win


def _patch_critical(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    shown: list[str] = []
    monkeypatch.setattr(
        "prismic.ui.main_window.QMessageBox.critical",
        lambda *args, **kwargs: shown.append(args[-1]),
    )
    return shown


def test_incompatible_schema_version_shows_an_error_not_a_crash(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "future_collection"
    root.mkdir()
    database_path = root / "future_collection.prismic"
    connection = database.connect(database_path)
    connection.execute(f"PRAGMA user_version = {len(migrations.MIGRATIONS) + 1}")
    connection.close()

    shown = _patch_critical(monkeypatch)

    window.open_collection(root)

    assert window.session is None
    assert len(shown) == 1


def test_opening_a_collection_already_locked_elsewhere_shows_an_error(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "vacation"
    root.mkdir()

    holder = PrismicSession.open(root)
    holder.initial_reconciliation.result(timeout=10)
    try:
        shown = _patch_critical(monkeypatch)

        window.open_collection(root)

        assert window.session is None
        assert len(shown) == 1
    finally:
        holder.close()

    # And now that it's released, the same window can open it normally.
    window.open_collection(root)
    qtbot.waitUntil(lambda: window.session is not None, timeout=5000)
