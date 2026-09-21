"""Bridges real Qt key events onto the Phase 3 input-resolution scaffolding.

No key is named in this file. `key_text()` turns a `QKeyEvent` into a
portable key-sequence string ("Ctrl+Z", "Space", "Left", "1"), and
everything downstream asks `ShortcutBindings` which command -- if any --
that string is currently bound to. That indirection is what makes every
shortcut user-configurable: rebinding one in Settings changes the lookup,
not any code here. See `application/input/shortcuts.py` for the registry
itself.

Text-editing precedence is handled by Qt's own focus system, not
reimplemented here: a focused `QLineEdit`/`QInputDialog` receives key events
directly, so this controller's `handle_key_press` never runs the rest of its
dispatch for those keys -- Qt delivers input to whatever's focused first,
before it would ever reach the main window. The two "works while typing"
navigation shortcuts are a deliberate exception: Up/Down (by default) have
no meaning in a single-line text field, unlike Left/Right which move the
caret, so result-list navigation stays reachable even while a tag search/
rename box has focus -- see the `text_editing` branch below. Quick-select
tag shortcuts are a second, narrower exception -- see below.

The tag-search cycle shortcut (Tab by default) fires immediately, in
`MainWindow.eventFilter`, with no chord/timeout involved -- once focus
actually lands in that search box (a QLineEdit), `text_editing` becomes
true and this controller stops seeing it at all. What happens from there
on is `MainWindow`'s doing: its event filter checks for that binding ahead
of ever calling in here, and while focus is in either tag search box,
redirects it to the other one directly (Qt's tab-order chain turns out not
to be able to represent a closed 2-widget loop -- see
`_cycle_tag_search_focus` for why plain `setTabOrder` doesn't work).

Focus mode is deliberately *not* bound here as a `QShortcut` the way the
viewer's play/pause button binds its own -- it's dispatched as a plain
`GLOBAL_COMMAND` key instead, which only ever runs when Qt delivers an
actual `KeyPress` event to this controller. Both default to Space; while
a video is showing, the play/pause button's own shortcut is what's
visible/enabled, and Qt's shortcut map consumes the key before a
`KeyPress` is ever delivered at all -- so `on_toggle_focus_mode` naturally
never fires in that case, and the two Space behaviors don't collide.
(That is also why `ShortcutScope` exists: the two live in different input
contexts, so Settings doesn't report the app's own default as a conflict.
The dismiss shortcut -- Escape by default -- is `MainWindow`'s fallback
out of focus mode for exactly the case this creates: entering focus mode
while viewing an image, then navigating to a video, leaves Space bound to
play/pause with no way back via this controller alone.)

Quick-select shortcuts (digits 0-9 by default) toggle whichever tag the
item-tags panel currently has numbered in that slot -- see
`TagListModel`/`TagRowDelegate` for the numbering itself, and
`MainWindow` for which side of the checked/unchecked split is currently
numbered. Only the non-text-editing case is handled here, though: while a
text box has focus, `MainWindow.eventFilter` intercepts them itself, ahead
of ever calling in here, since Ctrl+<that key> needs to insert a literal
character into that specific focused widget -- something this controller
has no widget access to do, being a plain callback dispatcher. (Emphasis
on *insert*: letting a Ctrl+digit `QKeyEvent` fall through to the widget
unhandled does not, in practice, type anything -- Windows hands Qt an
empty `text()` for most Ctrl+digit combinations, confirmed empirically
here, so passthrough alone would silently make those keys untypable in
these fields even with Ctrl held.)

The numbering-swap gesture (Ctrl tapped alone, nothing else pressed while
it's down) is a third, unrelated kind of shortcut, also handled entirely
in `MainWindow` -- it has no `QKeySequence` representation at all, so it
can't be resolved from a single key event. This controller has no notion
of that toggle, only of resolving whatever quick-select key was pressed
against whichever side is currently active.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QKeyCombination, QObject, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence

from prismic.application.input import shortcuts
from prismic.application.input.resolver import InputContext, InputEvent, InputResolver
from prismic.application.input.shortcuts import ShortcutBindings

_BARE_MODIFIER_KEYS: frozenset[int] = frozenset(
    {
        Qt.Key.Key_Control.value,
        Qt.Key.Key_Shift.value,
        Qt.Key.Key_Alt.value,
        Qt.Key.Key_Meta.value,
        Qt.Key.Key_AltGr.value,
    }
)

# Everything a key sequence can actually express. Keypad and
# group-switch are masked off deliberately: a numpad "1" should be the
# same shortcut as the row-of-digits "1", not an unbindable variant of
# it, and neither modifier survives a QKeySequence round trip anyway.
_SEQUENCE_MODIFIERS = (
    Qt.KeyboardModifier.ControlModifier
    | Qt.KeyboardModifier.ShiftModifier
    | Qt.KeyboardModifier.AltModifier
    | Qt.KeyboardModifier.MetaModifier
)

MODIFIER_KEY_NAMES: dict[int, str] = {
    Qt.Key.Key_Control.value: "Ctrl",
    Qt.Key.Key_Alt.value: "Alt",
    Qt.Key.Key_Shift.value: "Shift",
    Qt.Key.Key_Meta.value: "Meta",
}
"""Qt key -> the name a bare-modifier binding uses for it.

`key_text()` returns None for these, since a lone modifier has no key
sequence. A shortcut bound to one fires on the press/release pair
instead -- see `shortcuts.is_modifier_only()` and the tap tracking in
`MainWindow.eventFilter`."""


def key_text(event: QKeyEvent) -> str | None:
    """`event` as a portable key-sequence string, or None if it isn't one.

    Returns None for a bare modifier press (Ctrl on its own has no
    sequence representation -- the tap gesture that *does* use it is
    recognized from the press/release pair in `MainWindow.eventFilter`,
    not from a single event).
    """
    if event.key() in _BARE_MODIFIER_KEYS:
        return None
    combination = QKeyCombination(event.modifiers() & _SEQUENCE_MODIFIERS, Qt.Key(event.key()))
    text = QKeySequence(combination).toString(QKeySequence.SequenceFormat.PortableText)
    return text or None


def strip_control(binding: str) -> str | None:
    """`binding` without a leading "Ctrl+", or None if it had none.

    Used for the "Ctrl+<quick-select key> types the character instead of
    toggling a tag" escape hatch -- see `MainWindow.eventFilter`.
    """
    prefix = "Ctrl+"
    return binding[len(prefix) :] if binding.startswith(prefix) else None


def literal_character(binding: str) -> str | None:
    """The character `binding` would type if it weren't a shortcut, or
    None if it wouldn't type anything.

    Only single-character bindings qualify: "1" types "1" and "Q" types
    "q", but "F1" or "Left" type nothing at all, so there's nothing to
    hand back to a focused text box for those.
    """
    if len(binding) != 1:
        return None
    return binding.lower() if binding.isalpha() else binding


class KeyboardController(QObject):
    """Dispatches resolved key events to callbacks."""

    def __init__(
        self,
        bindings: ShortcutBindings,
        *,
        on_navigate_previous: Callable[[], None],
        on_navigate_next: Callable[[], None],
        on_undo: Callable[[], None],
        on_focus_item_tags: Callable[[], None],
        on_toggle_tag_shortcut: Callable[[int], None],
        on_toggle_focus_mode: Callable[[], None],
        on_swap_tag_numbering: Callable[[], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._bindings = bindings
        self._on_focus_item_tags = on_focus_item_tags
        self._on_toggle_tag_shortcut = on_toggle_tag_shortcut
        self._commands: dict[str, Callable[[], None]] = {
            shortcuts.NAVIGATE_PREVIOUS: on_navigate_previous,
            shortcuts.NAVIGATE_NEXT: on_navigate_next,
            shortcuts.NAVIGATE_PREVIOUS_WHILE_TYPING: on_navigate_previous,
            shortcuts.NAVIGATE_NEXT_WHILE_TYPING: on_navigate_next,
            shortcuts.FOCUS_TAG_SEARCH: on_focus_item_tags,
            shortcuts.FOCUS_MODE: on_toggle_focus_mode,
            # Registered here even though its default is a modifier tap,
            # which this controller never sees: the binding is the user's
            # to change, and on any ordinary key it has to dispatch like
            # every other command. Leaving it out would make it the one
            # shortcut that silently only works on a modifier.
            shortcuts.SWAP_TAG_NUMBERING: on_swap_tag_numbering,
        }
        # Undo is the one global command with no entry in `SHORTCUTS`:
        # Ctrl+Z is a platform-level editing convention rather than an
        # app-specific binding, and Qt's own text widgets implement it
        # themselves with no way to rebind theirs to match. Offering to
        # rebind only half of it would be worse than not offering at all.
        self._on_undo = on_undo

        self._resolver = InputResolver()
        self._resolver.register(InputContext.GLOBAL_COMMAND, self._handle_global_key)

    def run(self, shortcut_id: str) -> bool:
        """Run `shortcut_id`'s command directly, without a key event.

        The route in for a shortcut the user bound to a bare modifier:
        that gesture is recognized from a press/release pair in
        `MainWindow.eventFilter`, which then has an id in hand rather
        than a key to dispatch. Returns False for an id this controller
        doesn't own, so the caller can try elsewhere."""
        command = self._commands.get(shortcut_id)
        if command is None:
            return False
        command()
        return True

    def handle_key_press(self, event: QKeyEvent, *, text_editing: bool) -> bool:
        """Returns True if the event was consumed — the caller should
        `event.accept()` and not pass it on to base-class handling.

        `text_editing` is whether a text-entry widget currently has focus
        (a tag search/create box, an inline rename editor, ...). While
        true, only the two "works while typing" navigation shortcuts are
        honored, so normal typing works -- `MainWindow.eventFilter`
        handles quick-select keys itself in that case, ahead of ever
        calling in here (see this module's docstring for why)."""
        pressed = key_text(event)
        if pressed is None:
            return False
        if text_editing:
            for shortcut_id in (
                shortcuts.NAVIGATE_PREVIOUS_WHILE_TYPING,
                shortcuts.NAVIGATE_NEXT_WHILE_TYPING,
            ):
                if self._bindings.binding(shortcut_id) == pressed:
                    self._commands[shortcut_id]()
                    return True
            return False
        slot = self._bindings.quick_select_slot(pressed)
        if slot is not None:
            self._on_toggle_tag_shortcut(slot)
            return True
        if pressed == "Ctrl+Z":
            self._on_undo()
            return True
        return self._resolver.dispatch(InputEvent(key=pressed))

    def _handle_global_key(self, event: InputEvent) -> bool:
        shortcut_id = self._bindings.shortcut_for(event.key)
        command = self._commands.get(shortcut_id) if shortcut_id is not None else None
        if command is None:
            return False
        command()
        return True
