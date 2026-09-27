"""Wires hover-in/hover-out on static, fixed-identity controls (menu
actions, buttons) to `HoverExplainerBar.show_hint()`/`clear()`.

Registrations name a *shortcut id*, not a key: the keys are resolved from
`ShortcutBindings` at hover time, so rebinding something in Settings
updates its hover hint with nothing to re-register. A shortcut the user
has cleared shows its explanation with no keycaps rather than a stale key.

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

from prismic.application.input.shortcuts import ShortcutBindings, keycaps
from prismic.ui.hover_explainer_bar import HoverExplainerBar


class HoverHintController(QObject):
    def __init__(
        self, bar: HoverExplainerBar, bindings: ShortcutBindings, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._bar = bar
        self._bindings = bindings
        self._hints: dict[QObject, tuple[str, str]] = {}
        self._static_hints: dict[QObject, tuple[tuple[str, ...], str]] = {}

    def register_widget(self, widget: QWidget, shortcut_id: str, text: str) -> None:
        self._hints[widget] = (shortcut_id, text)
        widget.installEventFilter(self)

    def register_static(self, widget: QWidget, keys: tuple[str, ...], text: str) -> None:
        """Like `register_widget`, but for a hint whose keys aren't a
        rebindable `ShortcutBindings` entry -- undo/redo, which follow a
        fixed platform convention (see `keyboard.py`'s module docstring)
        rather than living in the shortcut registry."""
        self._static_hints[widget] = (keys, text)
        widget.installEventFilter(self)

    def register_action(self, action: QAction, menu: QMenu, shortcut_id: str, text: str) -> None:
        action.hovered.connect(lambda: self._show(shortcut_id, text))
        menu.aboutToHide.connect(self._bar.clear)

    def _show(self, shortcut_id: str, text: str) -> None:
        self._bar.show_hint(keycaps(self._bindings.binding(shortcut_id)), text)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        hint = self._hints.get(watched)
        if hint is not None:
            if event.type() == QEvent.Type.Enter:
                self._show(*hint)
            elif event.type() == QEvent.Type.Leave:
                self._bar.clear()
            return False
        static_hint = self._static_hints.get(watched)
        if static_hint is not None:
            if event.type() == QEvent.Type.Enter:
                self._bar.show_hint(*static_hint)
            elif event.type() == QEvent.Type.Leave:
                self._bar.clear()
        return False
