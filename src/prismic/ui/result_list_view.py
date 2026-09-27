"""The result list's own `QListView`, overriding mouse-press handling for
additive-only multi-select: shift-click selects the inclusive range
between the clicked row and whichever already-selected row sits closest
to it (by row distance), ctrl-click adds just the clicked row -- neither
ever *removes* anything already selected, unlike Qt's own default
`ExtendedSelection` behavior (whose shift-click replaces the selection
with a range from the last-clicked anchor, and whose ctrl-click toggles,
which can deselect).

A plain click with no modifier is left to Qt's own default handling
(`ExtendedSelection`'s ordinary click already does exactly what's wanted
here: replace the selection with just the clicked row), so this only
intercepts the two modified cases.

Selection itself lives entirely in Qt's own `QItemSelectionModel` --
this view doesn't track anything of its own. `MainWindow` reads the
resulting selection back out via `selectionModel().selectionChanged`
(see `_on_result_selection_changed`) the same way it already read
`currentChanged` for single-item selection.
"""

from __future__ import annotations

from PySide6.QtCore import QItemSelection, QItemSelectionModel, QModelIndex, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QAbstractItemView, QListView, QWidget


class ResultListView(QListView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Needed for more than one row to ever be highlighted at all --
        # the default `SingleSelection` mode won't keep a second row
        # selected no matter what `QItemSelectionModel` calls are made
        # against it.
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            super().mousePressEvent(event)
            return
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            self._select_range_from_nearest_selected(index)
            return
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            self._add_to_selection(index)
            return
        super().mousePressEvent(event)

    def _add_to_selection(self, index: QModelIndex) -> None:
        selection_model = self.selectionModel()
        selection_model.select(index, QItemSelectionModel.SelectionFlag.Select)
        # `NoUpdate`: moves the keyboard/shift-click anchor to the clicked
        # row without touching the selection `select()` just made -- the
        # default flags on `setCurrentIndex` would otherwise re-apply
        # `ExtendedSelection`'s plain-click behavior (clear-and-select)
        # right on top of it.
        selection_model.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)

    def _select_range_from_nearest_selected(self, index: QModelIndex) -> None:
        selection_model = self.selectionModel()
        selected_rows = sorted({i.row() for i in selection_model.selectedIndexes()})
        if not selected_rows:
            # Nothing to range from -- the closest sensible fallback is
            # exactly what ctrl-click does: just add this one row.
            self._add_to_selection(index)
            return
        clicked_row = index.row()
        nearest_row = min(selected_rows, key=lambda row: abs(row - clicked_row))
        low, high = sorted((nearest_row, clicked_row))
        model = self.model()
        assert model is not None
        top = model.index(low, 0)
        bottom = model.index(high, 0)
        selection_model.select(
            QItemSelection(top, bottom), QItemSelectionModel.SelectionFlag.Select
        )
        selection_model.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)
