"""Bridges real Qt key events onto the Phase 3 input-resolution scaffolding.

Text-editing precedence is handled by Qt's own focus system, not
reimplemented here: a focused `QLineEdit`/`QInputDialog` receives key events
directly, so this controller's `handle_key_press` never runs the rest of its
dispatch for those keys -- Qt delivers input to whatever's focused first,
before it would ever reach the main window. The one deliberate exception is
Up/Down: they have no meaning in a single-line text field (unlike Left/
Right, which move the caret), so result-list navigation stays reachable
even while a tag search/rename box has focus -- see the `text_editing`
branch below. What's left to arbitrate for everything else is chord state
(`LOCAL_MODAL`) versus plain navigation/commands (`GLOBAL_COMMAND`) -- a
separate `VIEWER` context isn't needed in practice yet, since nothing here
has viewer-specific keys that would conflict with a global one.

Two independent chords exist ("t" + digit, "Tab" + "Tab"), each with its
own `ChordState`/timer rather than sharing one: they resolve to different
things when a *lone* first key times out with nothing else pending -- "t"
alone resolves to nothing, a lone "Tab" focuses the item-tag box. A short
-lived first attempt gave the Tab chord its own much shorter timeout on the
theory that a lone Tab is a frequent command and shouldn't feel sluggish,
but a short window made the deliberate double-Tab unreliable to land in
practice, which matters more -- both chords now share the same timeout
(`_CHORD_TIMEOUT_SECONDS`), the Tab chord just via its own ChordState/timer
instance rather than by merging tables.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QKeyEvent

from prismic.application.input.chord import ChordState
from prismic.application.input.resolver import InputContext, InputEvent, InputResolver

_CHORD_TIMEOUT_SECONDS = 1.5
_TAB_CHORD_TIMEOUT_SECONDS = _CHORD_TIMEOUT_SECONDS

# "t" then a digit 1-9 toggles the Nth tag (in list order) on the current
# item -- one chord covers both "apply" and "remove" (whichever it isn't
# already is what pressing it does).
_CHORD_TABLE: dict[tuple[str, ...], str] = {
    ("t", str(digit)): f"toggle_tag_{digit - 1}" for digit in range(1, 10)
}
# "Tab" then a second "Tab" focuses the filter box instead of the item-tag
# box a lone "Tab" focuses (see _on_tab_chord_timeout for the lone case).
_TAB_CHORD_TABLE: dict[tuple[str, ...], str] = {("Tab", "Tab"): "focus_filter"}


class KeyboardController(QObject):
    """Owns chord state and dispatches resolved key events to callbacks."""

    def __init__(
        self,
        *,
        on_navigate_previous: Callable[[], None],
        on_navigate_next: Callable[[], None],
        on_undo: Callable[[], None],
        on_focus_item_tags: Callable[[], None],
        on_focus_filter: Callable[[], None],
        on_toggle_tag_by_index: Callable[[int], None],
        on_chord_status_changed: Callable[[str], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._chord = ChordState(timeout_seconds=_CHORD_TIMEOUT_SECONDS)
        self._chord_timer = QTimer(self)
        self._chord_timer.setSingleShot(True)
        self._chord_timer.timeout.connect(self._on_chord_timeout)

        self._tab_chord = ChordState(timeout_seconds=_TAB_CHORD_TIMEOUT_SECONDS)
        self._tab_chord_timer = QTimer(self)
        self._tab_chord_timer.setSingleShot(True)
        self._tab_chord_timer.timeout.connect(self._on_tab_chord_timeout)

        self._on_navigate_previous = on_navigate_previous
        self._on_navigate_next = on_navigate_next
        self._on_undo = on_undo
        self._on_focus_item_tags = on_focus_item_tags
        self._on_focus_filter = on_focus_filter
        self._on_toggle_tag_by_index = on_toggle_tag_by_index
        self._on_chord_status_changed = on_chord_status_changed

        self._resolver = InputResolver()
        self._resolver.register(InputContext.LOCAL_MODAL, self._handle_chord_key)
        self._resolver.register(InputContext.GLOBAL_COMMAND, self._handle_global_key)

    def handle_key_press(self, event: QKeyEvent, *, text_editing: bool) -> bool:
        """Returns True if the event was consumed — the caller should
        `event.accept()` and not pass it on to base-class handling.

        `text_editing` is whether a text-entry widget currently has focus
        (a tag search/create box, an inline rename editor, ...). While
        true, everything except Up/Down is left alone entirely so normal
        typing works -- Up/Down are handled directly, ahead of the chord/
        global resolver, since result-list navigation should work no
        matter where the caret is."""
        key_text = _key_text(event)
        if key_text is None:
            return False
        if text_editing:
            if key_text == "Up":
                self._on_navigate_previous()
                return True
            if key_text == "Down":
                self._on_navigate_next()
                return True
            return False
        return self._resolver.dispatch(InputEvent(key=key_text))

    @property
    def chord_is_pending(self) -> bool:
        return self._chord.is_pending or self._tab_chord.is_pending

    def _handle_chord_key(self, event: InputEvent) -> bool:
        if self._chord.is_pending:
            return self._advance_chord(event)
        if self._tab_chord.is_pending:
            return self._advance_tab_chord(event)
        return False  # no chord in progress -- let GLOBAL_COMMAND try it

    def _advance_chord(self, event: InputEvent) -> bool:
        if event.key == "Escape":
            self._cancel_chord()
            return True
        self._chord.press(event.key)
        self._chord_timer.start(int(_CHORD_TIMEOUT_SECONDS * 1000))
        command = self._chord.match(_CHORD_TABLE)
        if command is not None:
            self._run_chord_command(command)
        self._update_chord_status()
        return True

    def _advance_tab_chord(self, event: InputEvent) -> bool:
        if event.key == "Escape":
            self._cancel_tab_chord()
            return True
        self._tab_chord.press(event.key)
        self._tab_chord_timer.start(int(_TAB_CHORD_TIMEOUT_SECONDS * 1000))
        command = self._tab_chord.match(_TAB_CHORD_TABLE)
        if command == "focus_filter":
            self._on_focus_filter()
        self._update_chord_status()
        return True

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
        if event.key == "t":
            self._chord.press("t")
            self._chord_timer.start(int(_CHORD_TIMEOUT_SECONDS * 1000))
            self._update_chord_status()
            return True
        if event.key == "Tab":
            self._tab_chord.press("Tab")
            self._tab_chord_timer.start(int(_TAB_CHORD_TIMEOUT_SECONDS * 1000))
            self._update_chord_status()
            return True
        return False

    def _run_chord_command(self, command: str) -> None:
        if command.startswith("toggle_tag_"):
            index = int(command.removeprefix("toggle_tag_"))
            self._on_toggle_tag_by_index(index)

    def _cancel_chord(self) -> None:
        self._chord.cancel()
        self._chord_timer.stop()
        self._update_chord_status()

    def _cancel_tab_chord(self) -> None:
        self._tab_chord.cancel()
        self._tab_chord_timer.stop()
        self._update_chord_status()

    def _on_chord_timeout(self) -> None:
        self._chord.advance_time(_CHORD_TIMEOUT_SECONDS)
        self._update_chord_status()

    def _on_tab_chord_timeout(self) -> None:
        # Unlike "t" alone timing out (which resolves to nothing), a lone
        # "Tab" left pending until it times out -- no second "Tab" arrived
        # to complete the ("Tab", "Tab") chord -- resolves to its own
        # command: focus the item-tag box.
        pending = self._tab_chord.pending_keys
        timed_out = self._tab_chord.advance_time(_TAB_CHORD_TIMEOUT_SECONDS)
        if timed_out and pending == ("Tab",):
            self._on_focus_item_tags()
        self._update_chord_status()

    def _update_chord_status(self) -> None:
        if self._chord.is_pending:
            self._on_chord_status_changed(" ".join(self._chord.pending_keys) + " …")
        elif self._tab_chord.is_pending:
            self._on_chord_status_changed(" ".join(self._tab_chord.pending_keys) + " …")
        else:
            self._on_chord_status_changed("")


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
    if key == Qt.Key.Key_Escape:
        return "Escape"
    if key == Qt.Key.Key_Z and modifiers & Qt.KeyboardModifier.ControlModifier:
        return "Ctrl+Z"
    text = event.text()
    if text and text.isprintable():
        return text
    return None
