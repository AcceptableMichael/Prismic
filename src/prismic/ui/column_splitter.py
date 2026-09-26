"""A QSplitter whose handles have a much larger hit area than their drawn
line.

A plain QSplitter's handle is both the draggable hit area and the visible
divider at once, so widening one widens the other -- a 1px-wide target is
fiddly to grab precisely, but a correspondingly thick divider line would be
a visible design change nobody asked for. This keeps the same 1px
BORDER_SUBTLE line, just centered inside a wider draggable handle. Painting
the line directly, rather than through the stylesheet rules
`QSplitter::handle` normally gets, is what makes that possible -- those
rules still apply as before to any splitter that doesn't opt into this
(the vertical tag splitter, in particular).
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSplitter, QSplitterHandle

from prismic.ui import theme

_LINE_WIDTH = 1


class _ColumnSplitterHandle(QSplitterHandle):
    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.fillRect(self._line_rect(), QColor(theme.BORDER_SUBTLE))

    def _line_rect(self) -> QRect:
        rect = self.rect()
        if self.orientation() == Qt.Orientation.Horizontal:
            offset = (rect.width() - _LINE_WIDTH) // 2
            return QRect(offset, 0, _LINE_WIDTH, rect.height())
        offset = (rect.height() - _LINE_WIDTH) // 2
        return QRect(0, offset, rect.width(), _LINE_WIDTH)


class ColumnSplitter(QSplitter):
    """A QSplitter whose handles use `_ColumnSplitterHandle` instead of the
    stylesheet-drawn default -- see module docstring."""

    def createHandle(self) -> QSplitterHandle:
        return _ColumnSplitterHandle(self.orientation(), self)
