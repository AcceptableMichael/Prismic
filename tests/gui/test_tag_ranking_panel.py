from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from prismic.application.tag_ranking_settings import (
    DEFAULT_CORRELATION_THRESHOLD,
    DEFAULT_MEGA_POPULAR_THRESHOLD,
    TagRankingSettingsStore,
)
from prismic.persistence.preferences import PreferencesStore
from prismic.ui.settings_dialog import TagRankingPanel


@pytest.fixture
def store(tmp_path: Path) -> TagRankingSettingsStore:
    return TagRankingSettingsStore(PreferencesStore(tmp_path / "preferences.json"))


@pytest.fixture
def panel(qtbot: QtBot, store: TagRankingSettingsStore) -> TagRankingPanel:
    widget = TagRankingPanel(store)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def test_fields_start_at_the_stored_values(panel: TagRankingPanel) -> None:
    assert panel.correlation_row.fraction == DEFAULT_CORRELATION_THRESHOLD
    assert panel.mega_popular_row.fraction == DEFAULT_MEGA_POPULAR_THRESHOLD


def test_editing_the_correlation_field_saves_and_emits_changed(
    qtbot: QtBot, panel: TagRankingPanel, store: TagRankingSettingsStore
) -> None:
    with qtbot.waitSignal(panel.changed, timeout=1000):
        panel.correlation_row._editor.setText("60")  # noqa: SLF001
        panel.correlation_row._editor.editingFinished.emit()  # noqa: SLF001

    assert panel.correlation_row.fraction == 0.6
    assert store.load().correlation_threshold == 0.6


def test_editing_the_mega_popular_field_saves_and_emits_changed(
    qtbot: QtBot, panel: TagRankingPanel, store: TagRankingSettingsStore
) -> None:
    with qtbot.waitSignal(panel.changed, timeout=1000):
        panel.mega_popular_row._editor.setText("25")  # noqa: SLF001
        panel.mega_popular_row._editor.editingFinished.emit()  # noqa: SLF001

    assert panel.mega_popular_row.fraction == 0.25
    assert store.load().mega_popular_threshold == 0.25


def test_reset_button_is_disabled_at_the_default(panel: TagRankingPanel) -> None:
    assert not panel.correlation_row._reset_button.isEnabled()  # noqa: SLF001


def test_changing_a_field_enables_its_reset_button(qtbot: QtBot, panel: TagRankingPanel) -> None:
    with qtbot.waitSignal(panel.changed, timeout=1000):
        panel.correlation_row._editor.setText("50")  # noqa: SLF001
        panel.correlation_row._editor.editingFinished.emit()  # noqa: SLF001

    assert panel.correlation_row._reset_button.isEnabled()  # noqa: SLF001


def test_reset_restores_the_default_and_saves_it(
    qtbot: QtBot, panel: TagRankingPanel, store: TagRankingSettingsStore
) -> None:
    panel.correlation_row._editor.setText("50")  # noqa: SLF001
    panel.correlation_row._editor.editingFinished.emit()  # noqa: SLF001

    with qtbot.waitSignal(panel.changed, timeout=1000):
        panel.correlation_row._reset_button.click()  # noqa: SLF001

    assert panel.correlation_row.fraction == DEFAULT_CORRELATION_THRESHOLD
    assert store.load().correlation_threshold == DEFAULT_CORRELATION_THRESHOLD


def test_committing_the_same_value_does_not_emit_changed(
    qtbot: QtBot, panel: TagRankingPanel
) -> None:
    received: list[None] = []
    panel.changed.connect(lambda: received.append(None))

    panel.correlation_row._editor.editingFinished.emit()  # noqa: SLF001

    assert received == []
