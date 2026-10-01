"""The one place that knows what every keyboard shortcut in the app *is*.

Every shortcut the user can press is declared once, here, as a
`ShortcutDefinition` in `SHORTCUTS`. Nothing else in the codebase is
allowed to hard-code a key: `ui/keyboard.py` dispatches by looking a
pressed key up in `ShortcutBindings`, `ui/main_window.py` pushes the
resolved bindings onto the menu actions and hover hints, and
`ui/settings_dialog.py` renders this list verbatim. That's what makes
"list every single shortcut and let the user configure each one"
mechanically true rather than a hand-maintained duplicate that drifts:
a shortcut that isn't in this file doesn't work, and one that is shows
up in Settings automatically.

Deliberately Qt-free. Bindings are plain strings in Qt's *portable* key-
sequence format ("Ctrl+Shift+O", "Space", "Left", "1", "Esc") because
that format round-trips exactly through `QKeySequence` in both
directions, but this module never imports Qt -- translating a real
`QKeyEvent` into one of these strings is `ui/keyboard.key_text()`'s job,
which keeps the registry unit-testable without a `QApplication` and keeps
the layer direction (`ui -> application`) intact.

An empty binding string means *unbound*, which is a legitimate
configuration: the user can clear a shortcut they don't want rather than
being forced to park it on some key.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from prismic.persistence.preferences import PreferencesStore

_PREFERENCES_KEY = "shortcuts"

QUICK_SELECT_SLOT_COUNT = 10
"""How many tag rows the item-tags panel numbers at a time -- see
`ui/tag_model.py`, which assigns slots 0..N-1 by position."""


MODIFIER_NAMES: tuple[str, ...] = ("Ctrl", "Alt", "Shift", "Meta")
"""The modifiers, by the name Qt's portable key-sequence format uses.

Two jobs: they're the prefixes `keycaps()` peels off a combination, and
on their own they're a legitimate binding meaning "tapped alone" (see
`is_modifier_only`).
"""


def is_modifier_only(binding: str) -> bool:
    """Whether `binding` is a bare modifier, i.e. a tap gesture.

    A modifier on its own can't be a key *press* shortcut -- there's no
    `QKeySequence` for "Ctrl, by itself", and holding Ctrl is how half
    the other shortcuts start. So a binding of just "Ctrl" means the
    modifier pressed and released with nothing else in between, which
    `MainWindow.eventFilter` recognizes from the press/release pair.

    Any shortcut may be bound this way; nothing about the registry
    singles out which ones can. The gesture is a property of what the
    user bound, not of the command.
    """
    return normalize(binding) in MODIFIER_NAMES


class ShortcutScope(Enum):
    """Which input context a shortcut is resolved in, per the overview's
    section 10 precedence chain.

    Only used for conflict detection: two shortcuts in *different* scopes
    may share a key without it being a mistake. That isn't a theoretical
    allowance -- Space is bound to both Focus Mode (global) and the
    viewer's play/pause button (viewer) by default, on purpose, and Qt
    resolves it to whichever is live (see `ui/keyboard.py`'s module
    docstring). Flagging the app's own shipped defaults as a conflict
    would make the warning worthless.

    `MODIFIER` is the same idea for a different reason: it holds bindings
    that aren't a command someone presses, but a modifier held down to
    change what some *other* key does -- `TYPE_LITERALLY_MODIFIER` is the
    only one today. It defaults to "Ctrl", same as the numbering swap's
    own tap gesture (`GLOBAL`) -- one is "tap Ctrl alone," the other is
    "hold Ctrl while pressing something else," and a user can have both
    on Ctrl at once without either ever getting in the other's way. That
    would read as a conflict if the two shared a scope.
    """

    GLOBAL = auto()
    VIEWER = auto()
    MODIFIER = auto()


@dataclass(frozen=True, slots=True)
class ShortcutDefinition:
    id: str
    category: str
    label: str
    description: str
    default: str
    scope: ShortcutScope = ShortcutScope.GLOBAL


# -- Shortcut ids -----------------------------------------------------------
# Named constants rather than bare strings at the call sites, so a typo is
# an AttributeError at import time instead of a shortcut that silently
# never fires.

OPEN_COLLECTION_FOLDER = "collection.open_folder"
OPEN_COLLECTION_FILE = "collection.open_file"
OPEN_SETTINGS = "collection.settings"

TOGGLE_THUMBNAILS = "view.toggle_thumbnails"
FOCUS_MODE = "view.focus_mode"
SWAP_TAG_NUMBERING = "view.swap_tag_numbering"
SHUFFLE_RESULTS = "view.shuffle_results"
TRUE_FULLSCREEN = "view.true_fullscreen"

NAVIGATE_PREVIOUS = "navigate.previous"
NAVIGATE_NEXT = "navigate.next"
NAVIGATE_PREVIOUS_WHILE_TYPING = "navigate.previous_while_typing"
NAVIGATE_NEXT_WHILE_TYPING = "navigate.next_while_typing"
HISTORY_BACK = "navigate.history_back"
HISTORY_FORWARD = "navigate.history_forward"

FOCUS_TAG_SEARCH = "tagging.focus_search"
DISMISS = "tagging.dismiss"
TYPE_LITERALLY_MODIFIER = "tagging.type_literally_modifier"


def quick_select_id(slot: int) -> str:
    """The shortcut id for quick-select slot `slot` (0-based)."""
    return f"tagging.quick_select_{slot + 1}"


VIEWER_PLAY_PAUSE = "viewer.play_pause"


_QUICK_SELECT_DEFAULTS: tuple[str, ...] = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")

_TYPE_LITERALLY_LABEL = "Type the key instead of toggling"


def _quick_select_definitions() -> Iterator[ShortcutDefinition]:
    for slot in range(QUICK_SELECT_SLOT_COUNT):
        # Only the first of these ten spells out the modifier escape
        # hatch -- see TYPE_LITERALLY_MODIFIER just above, which every
        # slot shares equally. Repeating the same paragraph ten times
        # over would bury the one thing worth reading in nine copies of
        # it.
        description = (
            f"Toggle whichever tag the Edit list currently numbers {slot + 1} "
            "on the file being viewed"
        )
        if slot == 0:
            description += (
                f'. Still works while a tag search box has focus -- see "'
                f'{_TYPE_LITERALLY_LABEL}" above to type the key there instead'
            )
        yield ShortcutDefinition(
            id=quick_select_id(slot),
            category="Tagging",
            label=f"Toggle numbered tag {slot + 1}",
            description=description,
            default=_QUICK_SELECT_DEFAULTS[slot],
        )


SHORTCUTS: tuple[ShortcutDefinition, ...] = (
    ShortcutDefinition(
        id=OPEN_COLLECTION_FOLDER,
        category="Collection",
        label="Open collection folder",
        description="Open a folder as a collection",
        default="Ctrl+O",
    ),
    ShortcutDefinition(
        id=OPEN_COLLECTION_FILE,
        category="Collection",
        label="Open .prismic file",
        description="Open an existing .prismic collection file",
        default="Ctrl+Shift+O",
    ),
    ShortcutDefinition(
        id=OPEN_SETTINGS,
        category="Collection",
        label="Settings",
        description="Open this settings window",
        default="Ctrl+,",
    ),
    ShortcutDefinition(
        id=TOGGLE_THUMBNAILS,
        category="View",
        label="Show thumbnails",
        description="Toggle thumbnail previews in the results list",
        default="Ctrl+T",
    ),
    ShortcutDefinition(
        id=FOCUS_MODE,
        category="View",
        label="Focus mode",
        description="Hide every panel except the media viewer",
        default="Space",
    ),
    ShortcutDefinition(
        id=SWAP_TAG_NUMBERING,
        category="View",
        label="Swap which tags are numbered",
        description="Switch the Edit list's numbering between unselected and selected tags",
        default="Ctrl",
    ),
    ShortcutDefinition(
        id=SHUFFLE_RESULTS,
        category="View",
        label="Shuffle",
        description="Randomly reorder the currently filtered items in the results list",
        default="Ctrl+R",
    ),
    ShortcutDefinition(
        id=TRUE_FULLSCREEN,
        category="View",
        label="Full screen",
        description=(
            "Fill the whole screen, with no window frame -- any key press or click exits it again"
        ),
        default="Ctrl+F",
    ),
    ShortcutDefinition(
        id=NAVIGATE_PREVIOUS,
        category="Navigation",
        label="Previous file",
        description="Move to the previous file in the results list",
        default="Left",
    ),
    ShortcutDefinition(
        id=NAVIGATE_NEXT,
        category="Navigation",
        label="Next file",
        description="Move to the next file in the results list",
        default="Right",
    ),
    ShortcutDefinition(
        id=NAVIGATE_PREVIOUS_WHILE_TYPING,
        category="Navigation",
        label="Previous file (works while typing)",
        description="Move to the previous file even while a tag search box has focus",
        default="Up",
    ),
    ShortcutDefinition(
        id=NAVIGATE_NEXT_WHILE_TYPING,
        category="Navigation",
        label="Next file (works while typing)",
        description="Move to the next file even while a tag search box has focus",
        default="Down",
    ),
    ShortcutDefinition(
        id=HISTORY_BACK,
        category="Navigation",
        label="Back in view history",
        description=(
            "Return to the file viewed before this one, even if the current filter "
            "no longer includes it. Works while typing"
        ),
        default="Ctrl+Left",
    ),
    ShortcutDefinition(
        id=HISTORY_FORWARD,
        category="Navigation",
        label="Forward in view history",
        description=(
            "Undo a Back: go to the file viewed after this one, even if the current "
            "filter no longer includes it. Works while typing"
        ),
        default="Ctrl+Right",
    ),
    ShortcutDefinition(
        id=FOCUS_TAG_SEARCH,
        category="Tagging",
        label="Cycle tag search boxes",
        description="Jump to the Edit search box, then the Filter one, then back to browsing",
        default="Tab",
    ),
    ShortcutDefinition(
        id=DISMISS,
        category="Tagging",
        label="Dismiss",
        description="Leave the tag search box, and exit focus mode",
        default="Esc",
    ),
    ShortcutDefinition(
        id=TYPE_LITERALLY_MODIFIER,
        category="Tagging",
        label=_TYPE_LITERALLY_LABEL,
        description=(
            "Hold this modifier while pressing a numbered-tag shortcut's key, in a "
            "tag search box, to type that key instead of toggling the tag"
        ),
        default="Ctrl",
        scope=ShortcutScope.MODIFIER,
    ),
    *_quick_select_definitions(),
    ShortcutDefinition(
        id=VIEWER_PLAY_PAUSE,
        category="Viewer",
        label="Play or pause",
        description="Play or pause the video currently being viewed",
        default="Space",
        scope=ShortcutScope.VIEWER,
    ),
)

_BY_ID: dict[str, ShortcutDefinition] = {definition.id: definition for definition in SHORTCUTS}

CATEGORY_ORDER: tuple[str, ...] = tuple(
    dict.fromkeys(definition.category for definition in SHORTCUTS)
)
"""Every category, in the order it first appears in `SHORTCUTS` -- which
is also the order Settings renders them in, so reordering the list above
reorders the UI with no second list to keep in sync."""


def definition(shortcut_id: str) -> ShortcutDefinition:
    return _BY_ID[shortcut_id]


def normalize(binding: str) -> str:
    return binding.strip()


def keycaps(binding: str) -> tuple[str, ...]:
    """Split a binding into one label per physical key, for rendering as
    keycap boxes (`HoverExplainerBar`, the Settings rows).

    Peels known modifier prefixes off the front rather than splitting on
    "+", because "+" is also a bindable key: a plain `split("+")` turns
    "Ctrl++" into three segments (two of them empty) instead of the two
    keys it actually is.
    """
    binding = normalize(binding)
    if not binding:
        return ()
    parts: list[str] = []
    remaining = binding
    while True:
        for modifier in MODIFIER_NAMES:
            if remaining.startswith(f"{modifier}+"):
                parts.append(modifier)
                remaining = remaining[len(modifier) + 1 :]
                break
        else:
            break
    if remaining:
        parts.append(remaining)
    return tuple(parts)


class ShortcutBindings:
    """The currently-configured binding for every shortcut, persisted to
    the app-wide preferences file.

    Only *overrides* are stored, not the full table: a shortcut the user
    never touched follows its `default` forever, so changing a default in
    `SHORTCUTS` reaches everyone who hadn't already customized that one.
    """

    def __init__(self, store: PreferencesStore | None = None) -> None:
        self._store = store if store is not None else PreferencesStore()
        self._overrides: dict[str, str] = {}
        self._load()

    # -- Reading ------------------------------------------------------------

    @property
    def definitions(self) -> tuple[ShortcutDefinition, ...]:
        return SHORTCUTS

    def binding(self, shortcut_id: str) -> str:
        """The key currently bound to `shortcut_id`, or "" if unbound."""
        override = self._overrides.get(shortcut_id)
        if override is not None:
            return override
        return _BY_ID[shortcut_id].default

    def is_default(self, shortcut_id: str) -> bool:
        return shortcut_id not in self._overrides

    def shortcut_for(self, binding: str, scope: ShortcutScope = ShortcutScope.GLOBAL) -> str | None:
        """The id of the shortcut `binding` currently triggers in `scope`,
        or None if nothing is bound to it.

        An unbound shortcut (binding "") never matches, so a cleared
        shortcut can't be fired by some unrelated key normalizing to the
        empty string."""
        binding = normalize(binding)
        if not binding:
            return None
        for definition_ in SHORTCUTS:
            if definition_.scope is scope and self.binding(definition_.id) == binding:
                return definition_.id
        return None

    def quick_select_slot(self, binding: str) -> int | None:
        """The quick-select slot `binding` toggles, or None."""
        binding = normalize(binding)
        if not binding:
            return None
        for slot in range(QUICK_SELECT_SLOT_COUNT):
            if self.binding(quick_select_id(slot)) == binding:
                return slot
        return None

    def literal_typing_modifier(self) -> str:
        """The modifier that types a quick-select key literally instead of
        toggling it, while a tag search box has focus -- see
        `TYPE_LITERALLY_MODIFIER`. "" if unbound, which turns the escape
        hatch off entirely rather than leaving it stuck on some key."""
        return self.binding(TYPE_LITERALLY_MODIFIER)

    def conflicts(self, shortcut_id: str, binding: str) -> tuple[str, ...]:
        """Other shortcuts in the same scope already using `binding`."""
        binding = normalize(binding)
        if not binding:
            return ()
        scope = _BY_ID[shortcut_id].scope
        return tuple(
            other.id
            for other in SHORTCUTS
            if other.id != shortcut_id
            and other.scope is scope
            and self.binding(other.id) == binding
        )

    # -- Writing ------------------------------------------------------------

    def set_binding(self, shortcut_id: str, binding: str) -> None:
        binding = normalize(binding)
        if binding == _BY_ID[shortcut_id].default:
            self._overrides.pop(shortcut_id, None)
        else:
            self._overrides[shortcut_id] = binding
        self._save()

    def reset(self, shortcut_id: str) -> None:
        if self._overrides.pop(shortcut_id, None) is not None:
            self._save()

    def reset_all(self) -> None:
        if self._overrides:
            self._overrides.clear()
            self._save()

    # -- Persistence ---------------------------------------------------------

    def _load(self) -> None:
        stored: Any = self._store.load().get(_PREFERENCES_KEY)
        if not isinstance(stored, dict):
            return
        for shortcut_id, binding in stored.items():
            # Anything unrecognized is dropped rather than carried along:
            # this file is hand-editable, and a stale id from an older
            # build (or a typo) shouldn't survive the next save to keep
            # confusing whoever reads it.
            if shortcut_id in _BY_ID and isinstance(binding, str):
                self._overrides[shortcut_id] = normalize(binding)

    def _save(self) -> None:
        data = self._store.load()
        if self._overrides:
            data[_PREFERENCES_KEY] = dict(self._overrides)
        else:
            data.pop(_PREFERENCES_KEY, None)
        self._store.save(data)
