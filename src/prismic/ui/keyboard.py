"""Bridges real Qt key events onto the Phase 3 input-resolution scaffolding.

Text-editing precedence is handled by Qt's own focus system, not
reimplemented here: a focused `QLineEdit`/`QInputDialog` receives key events
directly, so this controller's `handle_key_press` never runs the rest of its
dispatch for those keys -- Qt delivers input to whatever's focused first,
before it would ever reach the main window. Up/Down are a deliberate
exception: they have no meaning in a single-line text field (unlike Left/
Right, which move the caret), so result-list navigation stays reachable
even while a tag search/rename box has focus -- see the `text_editing`
branch below. Digit keys are a second, narrower exception -- see below.

Tab fires `on_focus_item_tags` immediately, right here, with no chord/
timeout involved -- once focus actually lands in that search box (a
QLineEdit), `text_editing` becomes true and this controller stops seeing
Tab at all. What happens to it from there on is `MainWindow`'s doing, not
this controller's: `MainWindow.eventFilter` checks for Tab ahead of ever
calling into here, and while focus is in either tag search box, redirects
it to the other one directly (Qt's tab-order chain turns out not to be
able to represent a closed 2-widget loop -- see `_cycle_tag_search_focus`
for why plain `setTabOrder` doesn't work for this).

Space is deliberately *not* bound here as a `QShortcut` the way the
viewer's play/pause button binds it -- it's dispatched as a plain
`GLOBAL_COMMAND` key instead, which only ever runs when Qt delivers an
actual `KeyPress` event to this controller. While a video is showing, the
play/pause button's own Space shortcut is what's visible/enabled, and Qt's
shortcut map consumes the key before a `KeyPress` is ever delivered at
all -- so `on_toggle_focus_mode` naturally never fires in that case, and
the two Space behaviors don't collide. (Escape is `MainWindow`'s fallback
out of focus mode for exactly the case this creates: entering focus mode
while viewing an image, then navigating to a video, leaves Space bound to
play/pause with no way back via this controller alone.)

Digit keys (0-9) toggle whichever tag the item-tags panel currently has
numbered on that digit -- see `TagListModel`/`TagRowDelegate` for the
numbering itself, and `MainWindow` for which side of the checked/unchecked
split is currently numbered. Only the non-text-editing case is handled
here, though: while a text box has focus, `MainWindow.eventFilter`
intercepts digits itself, ahead of ever calling in here, since Ctrl+digit
needs to insert a literal character into that specific focused widget --
something this controller has no widget access to do, being a plain
callback dispatcher. (Emphasis on *insert*: letting a Ctrl+digit
`QKeyEvent` fall through to the widget unhandled does not, in practice,
type anything -- Windows hands Qt an empty `text()` for most Ctrl+digit
combinations, confirmed empirically here, so passthrough alone would
silently make digits untypable in these fields even with Ctrl held.)
Ctrl on its own (tapped alone, nothing else pressed while it's down) is a
third, unrelated gesture, also handled entirely in `MainWindow`, that
toggles which side of the checked/unchecked split gets numbered at all;
this controller has no notion of that toggle, only of resolving whatever
digit was pressed against whichever side is currently active.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QKeyEvent

from prismic.application.input.resolver import InputContext, InputEvent, InputResolver

DIGIT_KEYS: dict[int, int] = {
    Qt.Key.Key_0: 0,
    Qt.Key.Key_1: 1,
    Qt.Key.Key_2: 2,
    Qt.Key.Key_3: 3,
    Qt.Key.Key_4: 4,
    Qt.Key.Key_5: 5,
    Qt.Key.Key_6: 6,
    Qt.Key.Key_7: 7,
    Qt.Key.Key_8: 8,
    Qt.Key.Key_9: 9,
}


class KeyboardController(QObject):
    """Dispatches resolved key events to callbacks."""

    def __init__(
        self,
        *,
        on_navigate_previous: Callable[[], None],
        on_navigate_next: Callable[[], None],
        on_undo: Callable[[], None],
        on_focus_item_tags: Callable[[], None],
        on_toggle_tag_shortcut: Callable[[int], None],
        on_toggle_focus_mode: Callable[[], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_navigate_previous = on_navigate_previous
        self._on_navigate_next = on_navigate_next
        self._on_undo = on_undo
        self._on_focus_item_tags = on_focus_item_tags
        self._on_toggle_tag_shortcut = on_toggle_tag_shortcut
        self._on_toggle_focus_mode = on_toggle_focus_mode

        self._resolver = InputResolver()
        self._resolver.register(InputContext.GLOBAL_COMMAND, self._handle_global_key)

    def handle_key_press(self, event: QKeyEvent, *, text_editing: bool) -> bool:
        """Returns True if the event was consumed — the caller should
        `event.accept()` and not pass it on to base-class handling.

        `text_editing` is whether a text-entry widget currently has focus
        (a tag search/create box, an inline rename editor, ...). While
        true, everything except Up/Down is left alone entirely so normal
        typing works -- `MainWindow.eventFilter` handles digits itself in
        that case, ahead of ever calling in here (see this module's
        docstring for why)."""
        if text_editing:
            key_text = _key_text(event)
            if key_text == "Up":
                self._on_navigate_previous()
                return True
            if key_text == "Down":
                self._on_navigate_next()
                return True
            return False
        digit = DIGIT_KEYS.get(event.key())
        if digit is not None:
            self._on_toggle_tag_shortcut(digit)
            return True
        key_text = _key_text(event)
        if key_text is None:
            return False
        return self._resolver.dispatch(InputEvent(key=key_text))

    def _handle_global_key(self, event: InputEvent) -> bool:
        if event.key in ("Left", "Up"):
            self._on_navigate_previous()
            return True
        if event.key in ("Right", "Down"):
            self._on_navigate_next()
            return True
        if event.key == "Ctrl+Z":
            self._on_undo()
            return True
        if event.key == "Tab":
            self._on_focus_item_tags()
            return True
        if event.key == "Space":
            self._on_toggle_focus_mode()
            return True
        return False


def _key_text(event: QKeyEvent) -> str | None:
    key = event.key()
    modifiers = event.modifiers()
    if key == Qt.Key.Key_Left:
        return "Left"
    if key == Qt.Key.Key_Right:
        return "Right"
    if key == Qt.Key.Key_Up:
        return "Up"
    if key == Qt.Key.Key_Down:
        return "Down"
    if key == Qt.Key.Key_Tab:
        return "Tab"
    if key == Qt.Key.Key_Space:
        return "Space"
    if key == Qt.Key.Key_Escape:
        return "Escape"
    if key == Qt.Key.Key_Z and modifiers & Qt.KeyboardModifier.ControlModifier:
        return "Ctrl+Z"
    text = event.text()
    if text and text.isprintable():
        return text
    return None
