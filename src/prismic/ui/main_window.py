"""Main application window.

This is a neutral placeholder shell. Real collection UI (tag list, filter
selection, result view, viewer) lands in Phase 5 once the application layer
underneath it exists; until then this window intentionally does nothing more
than establish the top-level frame so it isn't mistaken for product behavior.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Prismic")
        self.resize(1024, 768)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.placeholder_label = QLabel("No collection open")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("font-size: 18px; color: #666;")
        layout.addWidget(self.placeholder_label)
