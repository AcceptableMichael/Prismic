"""Zoomable, pannable image display.

Panning and smooth scaling are QGraphicsView's own built-in behavior
(`ScrollHandDrag` mode) — leaned on rather than reimplemented.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QMouseEvent, QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QWidget

_ZOOM_STEP_IN = 1.25
_ZOOM_STEP_OUT = 1 / _ZOOM_STEP_IN
_DOUBLE_CLICK_ZOOM = 2.0


class ImageView(QGraphicsView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._zoom = 1.0
        self._fitted = True
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

    def set_image(self, image: QImage) -> None:
        self._scene.clear()
        pixmap = QPixmap.fromImage(image)
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.resetTransform()
        self._zoom = 1.0
        self._fitted = True
        self.fit_to_window()

    def clear(self) -> None:
        self._scene.clear()
        self._pixmap_item = None

    @property
    def zoom(self) -> float:
        return self._zoom

    def fit_to_window(self) -> None:
        if self._pixmap_item is None:
            return
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = 1.0
        self._fitted = True

    def zoom_in(self) -> None:
        self._apply_zoom(_ZOOM_STEP_IN)

    def zoom_out(self) -> None:
        self._apply_zoom(_ZOOM_STEP_OUT)

    def _apply_zoom(self, factor: float) -> None:
        if self._pixmap_item is None:
            return
        self.scale(factor, factor)
        self._zoom *= factor
        self._fitted = False

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._pixmap_item is None:
            super().wheelEvent(event)
            return
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._pixmap_item is not None:
            if self._fitted:
                self.resetTransform()
                self.scale(_DOUBLE_CLICK_ZOOM, _DOUBLE_CLICK_ZOOM)
                self._zoom = _DOUBLE_CLICK_ZOOM
                self._fitted = False
            else:
                self.fit_to_window()
        super().mouseDoubleClickEvent(event)
