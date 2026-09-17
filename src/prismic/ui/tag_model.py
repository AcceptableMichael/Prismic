"""A checkable Qt list model over a collection's tags.

Reused for two different purposes in the UI, each with a different notion
of "checked": the filter panel (checked = part of the active filter) and
the viewer's per-item tag panel (checked = mapped to the current item).
Which one a given instance represents is entirely up to whatever supplies
its `selected_tag_ids` — the model itself is agnostic.

Display-only: it never talks to the database itself. Toggling a checkbox
emits `toggle_requested`, and the checked state doesn't actually change
until whoever's listening dispatches the corresponding command and calls
`set_tags()` again with the new true state.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    Signal,
)

from prismic.domain.tag import Tag

_Index = QModelIndex | QPersistentModelIndex


class TagListModel(QAbstractListModel):
    toggle_requested = Signal(int)  # tag_id

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tags: list[Tag] = []
        self._selected_tag_ids: frozenset[int] = frozenset()

    def set_tags(self, tags: list[Tag], selected_tag_ids: frozenset[int]) -> None:
        self.beginResetModel()
        self._tags = tags
        self._selected_tag_ids = selected_tag_ids
        self.endResetModel()

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
        if role == Qt.ItemDataRole.CheckStateRole:
            is_selected = tag.id in self._selected_tag_ids
            return Qt.CheckState.Checked if is_selected else Qt.CheckState.Unchecked
        return None

    def setData(self, index: _Index, value: object, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.CheckStateRole:
            return False
        tag = self._tags[index.row()]
        self.toggle_requested.emit(tag.id)
        return True

    def flags(self, index: _Index) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
        )
