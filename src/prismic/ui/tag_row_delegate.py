"""Paints and drives interaction for a single row of `TagListModel`.

A custom delegate rather than Qt's built-in checkable-item machinery, for
one reason: the whole row must toggle the tag, not just a small checkbox
hit-target -- `editorEvent` hit-tests the row itself against the same
rects `paint()` draws, so there is exactly one source of truth for where
the checkbox, rename and delete affordances live. Clicking anywhere in a
row that isn't the rename/delete icon toggles it; those two icons only
*appear* on hover (see `theme.py`'s absence of any special-casing here --
visibility is entirely this delegate's own paint state), but are always
hit-testable at their drawn position, which is only ever reachable by a
pointer that is in fact hovering there.

Renaming reuses Qt's own inline-editor flow (`createEditor`/
`setEditorData`/`setModelData`) rather than a modal dialog: the pencil
icon calls `view.edit(index)`, and `setModelData` emits `rename_committed`
instead of writing into the model, since `TagListModel` is deliberately
display-only (see its docstring) -- the owning `TagPanel`/`MainWindow`
dispatches the actual `TagRenameCommand` and repopulates the model.

`show_shortcuts=True` (only ever passed for the item-tags panel's
instance) paints the digit `TagListModel` already computed for this row
into the checkbox itself -- painting only, no key handling here at all;
`KeyboardController`/`MainWindow` own resolving a pressed digit back to a
tag_id via the model's own `tag_id_for_shortcut()`, the same lookup this
delegate's numbers are drawn from, so there's one shared source of truth
for "what does this digit mean right now" between the paint and the
keypress.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractItemModel,
    QEvent,
    QModelIndex,
    QPersistentModelIndex,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
    SignalInstance,
)
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QLineEdit,
    QListView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from prismic.ui import theme
from prismic.ui.tag_model import CheckedRole, CheckedShortcutRole, TagIdRole, UncheckedShortcutRole

_Index = QModelIndex | QPersistentModelIndex

_ROW_HEIGHT = 32
_CHECKBOX_SIZE = 14
_ICON_SIZE = 18
_PAD = 8
_SHORTCUT_DIGIT_PIXEL_SIZE = 9  # small enough to fit inside a 14px checkbox


class TagRowDelegate(QStyledItemDelegate):
    toggle_requested = Signal(int)  # tag_id
    delete_requested = Signal(int)  # tag_id
    rename_committed = Signal(int, str)  # tag_id, new_name

    def __init__(
        self, list_view: QListView, parent: QWidget | None = None, *, show_shortcuts: bool = False
    ) -> None:
        super().__init__(parent)
        self._list_view = list_view
        # Only the item-tags ("Edit this file") panel's delegate is
        # constructed with this True -- the filter panel shows no numbers
        # at all, per MainWindow's wiring.
        self._show_shortcuts = show_shortcuts
        # Which side of the checked/unchecked split currently gets numbers
        # -- flipped by MainWindow when Ctrl is tapped alone, independent
        # of any row's own hover/paint state, hence a settable attribute
        # rather than something derived per-paint.
        self._show_checked_shortcuts = False

    def set_show_checked_shortcuts(self, value: bool) -> None:
        if value == self._show_checked_shortcuts:
            return
        self._show_checked_shortcuts = value
        self._list_view.viewport().update()

    def sizeHint(self, option: QStyleOptionViewItem, index: _Index) -> QSize:
        return QSize(option.rect.width(), _ROW_HEIGHT)

    def _rects(self, row_rect: QRect) -> tuple[QRect, QRect, QRect]:
        checkbox = QRect(
            row_rect.x() + _PAD,
            row_rect.y() + (row_rect.height() - _CHECKBOX_SIZE) // 2,
            _CHECKBOX_SIZE,
            _CHECKBOX_SIZE,
        )
        delete_rect = QRect(
            row_rect.right() - _PAD - _ICON_SIZE,
            row_rect.y() + (row_rect.height() - _ICON_SIZE) // 2,
            _ICON_SIZE,
            _ICON_SIZE,
        )
        rename_rect = QRect(
            delete_rect.x() - _ICON_SIZE - 2, delete_rect.y(), _ICON_SIZE, _ICON_SIZE
        )
        return checkbox, rename_rect, delete_rect

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: _Index) -> None:
        tag_id = index.data(TagIdRole)
        name = index.data(Qt.ItemDataRole.DisplayRole)
        if not isinstance(tag_id, int) or not isinstance(name, str):
            return
        checked = bool(index.data(CheckedRole))
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect
        if checked:
            painter.fillRect(rect, QColor(theme.SELECTED_WASH))
        elif hovered:
            painter.fillRect(rect, QColor(theme.HOVER_WASH))

        checkbox_rect, rename_rect, delete_rect = self._rects(rect)
        checkbox_path = QPainterPath()
        checkbox_path.addRoundedRect(
            float(checkbox_rect.x()),
            float(checkbox_rect.y()),
            float(checkbox_rect.width()),
            float(checkbox_rect.height()),
            4,
            4,
        )
        if checked:
            painter.fillPath(checkbox_path, QColor(theme.SELECTED_MARK))
        else:
            painter.setPen(QPen(QColor(theme.BORDER), 1.5))
            painter.drawPath(checkbox_path)

        if self._show_shortcuts:
            role = CheckedShortcutRole if self._show_checked_shortcuts else UncheckedShortcutRole
            digit = index.data(role)
            if isinstance(digit, int):
                self._paint_shortcut_digit(painter, checkbox_rect, digit)

        text_right = rename_rect.x() - _PAD if hovered else rect.right() - _PAD
        text_rect = QRect(
            checkbox_rect.right() + _PAD,
            rect.y(),
            text_right - checkbox_rect.right() - _PAD,
            rect.height(),
        )
        painter.setPen(QPen(QColor(theme.TEXT_PRIMARY)))
        metrics = painter.fontMetrics()
        elided = metrics.elidedText(name, Qt.TextElideMode.ElideMiddle, max(0, text_rect.width()))
        painter.drawText(
            text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided
        )

        if hovered:
            self._paint_icon(painter, rename_rect, "rename")
            self._paint_icon(painter, delete_rect, "delete")

        painter.restore()

    def _paint_icon(self, painter: QPainter, rect: QRect, kind: str) -> None:
        color = QColor(theme.TEXT_MUTED)
        painter.setPen(QPen(color, 1.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = rect.center().x(), rect.center().y()
        if kind == "rename":
            path = QPainterPath()
            path.moveTo(cx - 4, cy + 4)
            path.lineTo(cx + 3, cy - 3)
            path.moveTo(cx + 1, cy - 5)
            path.lineTo(cx + 5, cy - 1)
            path.lineTo(cx - 2, cy + 6)
            path.lineTo(cx - 5, cy + 5)
            path.lineTo(cx - 4, cy + 4)
            painter.drawPath(path)
        else:
            painter.drawLine(cx - 5, cy - 4, cx + 5, cy - 4)
            painter.drawRect(cx - 3, cy - 4, 6, 1)
            painter.drawRoundedRect(cx - 4, cy - 3, 8, 8, 1, 1)
            painter.drawLine(cx - 1, cy - 1, cx - 1, cy + 3)
            painter.drawLine(cx + 1, cy - 1, cx + 1, cy + 3)

    def _paint_shortcut_digit(self, painter: QPainter, checkbox_rect: QRect, digit: int) -> None:
        # One consistent green regardless of the checkbox's own outlined
        # (unchecked) or filled (checked) look -- not tuned separately per
        # background, since that look is due for a revisit anyway.
        painter.setPen(QPen(QColor(theme.KEYCAP_BORDER)))
        font = painter.font()
        font.setPixelSize(_SHORTCUT_DIGIT_PIXEL_SIZE)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(checkbox_rect, Qt.AlignmentFlag.AlignCenter, str(digit))

    def editorEvent(
        self,
        event: QEvent,
        model: QAbstractItemModel,
        option: QStyleOptionViewItem,
        index: _Index,
    ) -> bool:
        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
            tag_id = index.data(TagIdRole)
            if not isinstance(tag_id, int):
                return False
            pos = event.position().toPoint()
            _checkbox_rect, rename_rect, delete_rect = self._rects(option.rect)
            if delete_rect.contains(pos):
                self._emit_later(self.delete_requested, tag_id)
                return True
            if rename_rect.contains(pos):
                self._list_view.edit(index)
                return True
            self._emit_later(self.toggle_requested, tag_id)
            return True
        return super().editorEvent(event, model, option, index)

    def _emit_later(self, signal: SignalInstance, tag_id: int) -> None:
        # Whoever handles toggle/delete resets TagListModel (see
        # `TagPanel._apply_filter`), and doing that synchronously from
        # inside `editorEvent` -- while the view is still mid-dispatch of
        # the very mouse event that triggered it -- corrupted the *other*
        # list's state in practice (observed live: unchecking a filter tag
        # left the result list empty until an unrelated click elsewhere).
        # Queuing the emission lets this event finish unwinding first.
        QTimer.singleShot(0, lambda: signal.emit(tag_id))

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: _Index) -> QWidget:
        editor = QLineEdit(parent)
        editor.setObjectName("tagRenameEdit")
        # Not relying on QAbstractItemDelegate's own built-in Enter/Escape
        # handling here -- it didn't reliably fire for a delegate-supplied
        # editor in practice, so committing/cancelling is wired explicitly
        # instead of trusting an implicit base-class event filter.
        editor.installEventFilter(self)
        return editor

    def eventFilter(self, watched: QWidget, event: QEvent) -> bool:  # type: ignore[override]
        if isinstance(watched, QLineEdit) and event.type() == QEvent.Type.KeyPress:
            assert isinstance(event, QKeyEvent)
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.commitData.emit(watched)
                self.closeEditor.emit(watched)
                return True
            if event.key() == Qt.Key.Key_Escape:
                self.closeEditor.emit(watched, QStyledItemDelegate.EndEditHint.RevertModelCache)
                return True
        return super().eventFilter(watched, event)

    def setEditorData(self, editor: QWidget, index: _Index) -> None:
        assert isinstance(editor, QLineEdit)
        name = index.data(Qt.ItemDataRole.DisplayRole)
        editor.setText(name if isinstance(name, str) else "")
        editor.selectAll()

    def updateEditorGeometry(
        self, editor: QWidget, option: QStyleOptionViewItem, index: _Index
    ) -> None:
        checkbox_rect, _rename_rect, _delete_rect = self._rects(option.rect)
        editor.setGeometry(
            QRect(
                checkbox_rect.right() + _PAD,
                option.rect.y() + 2,
                option.rect.right() - checkbox_rect.right() - 2 * _PAD,
                option.rect.height() - 4,
            )
        )

    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: _Index) -> None:
        assert isinstance(editor, QLineEdit)
        tag_id = index.data(TagIdRole)
        new_name = editor.text().strip()
        if isinstance(tag_id, int) and new_name:
            self.rename_committed.emit(tag_id, new_name)
