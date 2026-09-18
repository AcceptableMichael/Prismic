"""Wires hover-in/hover-out on static, fixed-identity controls (menu
actions, buttons) to `HoverExplainerBar.show_hint()`/`clear()`.

Dynamic, per-row controls (tag list rows) don't go through here -- there's
no single QWidget per row to attach to, so `TagPanel` reports hovered row
indices via its own signal instead, and `MainWindow` resolves those to a
hint itself. This controller only covers the "one fixed widget/action per
shortcut" case.

QAction has no "unhovered" signal to pair with `hovered`, so clearing is
driven by the owning QMenu's `aboutToHide` instead -- whichever action was
last hovered (if any) is irrelevant at that point, the bar just clears.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QWidget

from prismic.ui.hover_explainer_bar import HoverExplainerBar


class HoverHintController(QObject):
    def __init__(self, bar: HoverExplainerBar, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._bar = bar
        self._hints: dict[QObject, tuple[tuple[str, ...], str]] = {}

    def register_widget(self, widget: QWidget, keys: tuple[str, ...], text: str) -> None:
        self._hints[widget] = (keys, text)
        widget.installEventFilter(self)

    def register_action(
        self, action: QAction, menu: QMenu, keys: tuple[str, ...], text: str
    ) -> None:
        action.hovered.connect(lambda: self._bar.show_hint(keys, text))
        menu.aboutToHide.connect(self._bar.clear)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        hint = self._hints.get(watched)
        if hint is not None:
            if event.type() == QEvent.Type.Enter:
                self._bar.show_hint(*hint)
            elif event.type() == QEvent.Type.Leave:
                self._bar.clear()
        return False
