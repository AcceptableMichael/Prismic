"""A passive Qt list model over a collection's tags.

Reused for two different purposes in the UI, each with a different notion
of "checked": the item-tags panel (checked = mapped to the current item)
and the filter panel (checked = part of the active filter). Which one a
given instance represents is entirely up to whatever supplies its
`selected_tag_ids` -- the model itself is agnostic.

Display-only, like `result_model.ResultListModel`: it never talks to the
database itself and holds no interaction logic of its own. Rows are
painted and clicked via `TagRowDelegate`/`TagPanel`, which read `TagIdRole`
and `CheckedRole` here and emit their own signals rather than writing back
through this model -- there is deliberately no `setData()`.

`UncheckedShortcutRole`/`CheckedShortcutRole` are computed here too (once,
in `set_tags()`) for the same reason `CheckedRole` is: this is the one
place that already knows each tag's checked state and the order it's
displayed in, so it's the natural place to number "the Nth unchecked tag"
without a second component re-deriving that split. Both roles are always
populated regardless of which panel this model backs -- the filter panel's
delegate just never reads them, since only the item-tags panel shows
shortcut numbers (see `MainWindow`).
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, QPersistentModelIndex, Qt

from prismic.domain.tag import Tag

_Index = QModelIndex | QPersistentModelIndex

TagIdRole = Qt.ItemDataRole.UserRole + 1
CheckedRole = Qt.ItemDataRole.UserRole + 2
# The digit (0-9) that toggles this tag when the item-tags panel's shortcut
# numbering is limited to unchecked (or checked) tags -- None past the
# first 10 tags in that state, or when this tag isn't in that state at
# all. See `_shortcut_digit_for_position` for the 1..9-then-0 ordering.
UncheckedShortcutRole = Qt.ItemDataRole.UserRole + 3
CheckedShortcutRole = Qt.ItemDataRole.UserRole + 4


def _shortcut_digit_for_position(position: int) -> int | None:
    if position < 9:
        return position + 1
    if position == 9:
        return 0
    return None


class TagListModel(QAbstractListModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tags: list[Tag] = []
        self._selected_tag_ids: frozenset[int] = frozenset()
        self._unchecked_shortcuts: dict[int, int] = {}
        self._checked_shortcuts: dict[int, int] = {}

    def set_tags(self, tags: list[Tag], selected_tag_ids: frozenset[int]) -> None:
        self.beginResetModel()
        self._tags = tags
        self._selected_tag_ids = selected_tag_ids
        self._unchecked_shortcuts = {}
        self._checked_shortcuts = {}
        unchecked_count = 0
        checked_count = 0
        for tag in tags:
            if tag.id in selected_tag_ids:
                digit = _shortcut_digit_for_position(checked_count)
                if digit is not None:
                    self._checked_shortcuts[tag.id] = digit
                checked_count += 1
            else:
                digit = _shortcut_digit_for_position(unchecked_count)
                if digit is not None:
                    self._unchecked_shortcuts[tag.id] = digit
                unchecked_count += 1
        self.endResetModel()

    def tag_id_for_shortcut(self, digit: int, *, selected: bool) -> int | None:
        """The tag currently bound to `digit` in the unchecked (or, with
        `selected=True`, checked) shortcut numbering -- the same mapping
        `data()` exposes per-row via `UncheckedShortcutRole`/
        `CheckedShortcutRole`, as one reverse lookup instead of a scan over
        every row."""
        table = self._checked_shortcuts if selected else self._unchecked_shortcuts
        for tag_id, bound_digit in table.items():
            if bound_digit == digit:
                return tag_id
        return None

    def tag_at(self, row: int) -> Tag:
        return self._tags[row]

    def row_for_tag_id(self, tag_id: int) -> int | None:
        for row, tag in enumerate(self._tags):
            if tag.id == tag_id:
                return row
        return None

    def rowCount(self, parent: _Index | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self._tags)

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not (0 <= index.row() < len(self._tags)):
            return None
        tag = self._tags[index.row()]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return tag.name
        if role == TagIdRole:
            return tag.id
        if role == CheckedRole:
            return tag.id in self._selected_tag_ids
        if role == UncheckedShortcutRole:
            return self._unchecked_shortcuts.get(tag.id)
        if role == CheckedShortcutRole:
            return self._checked_shortcuts.get(tag.id)
        return None

    def flags(self, index: _Index) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
