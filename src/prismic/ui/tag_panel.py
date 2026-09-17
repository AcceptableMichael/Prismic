"""A titled, checkable tag list, optionally with create/rename/delete
controls.

Purely a presentation shell around `TagListModel` — every user action comes
out as a Qt signal; nothing here calls into the application layer directly
(see `main_window.py`, which is what actually dispatches commands).
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListView,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from prismic.ui.tag_model import TagListModel


class TagPanel(QWidget):
    toggle_requested = Signal(int)  # tag_id
    create_requested = Signal(str)  # name
    rename_requested = Signal(int, str)  # tag_id, new_name
    delete_requested = Signal(int)  # tag_id

    def __init__(self, title: str, *, editable: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model = TagListModel(self)
        self.model.toggle_requested.connect(self.toggle_requested)

        self.list_view = QListView(self)
        self.list_view.setObjectName("tagList")
        self.list_view.setModel(self.model)

        title_label = QLabel(title.upper())
        title_label.setObjectName("panelTitle")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(title_label)
        layout.addWidget(self.list_view)

        if editable:
            buttons = QHBoxLayout()
            buttons.setContentsMargins(8, 8, 8, 8)
            add_button = QPushButton("New…")
            add_button.clicked.connect(self.prompt_new_tag)
            rename_button = QPushButton("Rename…")
            rename_button.clicked.connect(self._on_rename)
            delete_button = QPushButton("Delete")
            delete_button.setObjectName("dangerButton")
            delete_button.clicked.connect(self._on_delete)
            buttons.addWidget(add_button)
            buttons.addWidget(rename_button)
            buttons.addWidget(delete_button)
            layout.addLayout(buttons)

    def prompt_new_tag(self) -> None:
        name, confirmed = QInputDialog.getText(self, "New tag", "Tag name:")
        if confirmed and name.strip():
            self.create_requested.emit(name.strip())

    def _on_rename(self) -> None:
        index = self.list_view.currentIndex()
        if not index.isValid():
            return
        tag = self.model.tag_at(index.row())
        name, confirmed = QInputDialog.getText(self, "Rename tag", "New name:", text=tag.name)
        if confirmed and name.strip():
            self.rename_requested.emit(tag.id, name.strip())

    def _on_delete(self) -> None:
        index = self.list_view.currentIndex()
        if not index.isValid():
            return
        tag = self.model.tag_at(index.row())
        self.delete_requested.emit(tag.id)
