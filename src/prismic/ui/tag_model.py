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
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, QPersistentModelIndex, Qt

from prismic.domain.tag import Tag

_Index = QModelIndex | QPersistentModelIndex

TagIdRole = Qt.ItemDataRole.UserRole + 1
CheckedRole = Qt.ItemDataRole.UserRole + 2


class TagListModel(QAbstractListModel):
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
        if role == TagIdRole:
            return tag.id
        if role == CheckedRole:
            return tag.id in self._selected_tag_ids
        return None

    def flags(self, index: _Index) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
