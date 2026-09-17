import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_SPACE_GLYPH = "␣"  # visible "open box" stand-in for a literal space keycap


class KeycapDisplay(QWidget):
    """Renders each character of a string as its own keycap-style box."""

    def __init__(self) -> None:
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def set_text(self, text: str) -> None:
        self._clear()
        for character in text:
            self._layout.addWidget(self._make_keycap(character))

    def keycap_texts(self) -> list[str]:
        """The glyph currently shown on each keycap, left to right."""
        texts: list[str] = []
        for index in range(self._layout.count()):
            item = self._layout.itemAt(index)
            widget = item.widget() if item is not None else None
            assert isinstance(widget, QLabel)
            texts.append(widget.text())
        return texts

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _make_keycap(character: str) -> QLabel:
        label = QLabel(_SPACE_GLYPH if character == " " else character)
        label.setObjectName("keycap")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedSize(36, 36)
        label.setStyleSheet(
            """
            QLabel#keycap {
                background-color: #fafafa;
                border: 1px solid #b0b0b0;
                border-bottom: 3px solid #909090;
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 16px;
                font-weight: 600;
                color: #222;
            }
            """
        )
        return label


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Prismic")
        self.resize(1024, 768)

        self._central = QWidget()
        self.setCentralWidget(self._central)

        layout = QVBoxLayout(self._central)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)

        self.confirm_button = QPushButton("Confirm here")
        confirm_button = self.confirm_button
        confirm_button.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_button.setStyleSheet(
            """
            QPushButton {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4facfe, stop:1 #1565c0
                );
                color: white;
                font-size: 18px;
                font-weight: 600;
                border: none;
                border-radius: 12px;
                padding: 16px 40px;
            }
            QPushButton:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5fb8ff, stop:1 #1976d2
                );
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            """
        )
        confirm_button.clicked.connect(self._randomize_background)
        layout.addWidget(confirm_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.text_input = QLineEdit()
        self.text_input.setObjectName("keycap_input")
        self.text_input.setPlaceholderText("Type something…")
        self.text_input.setFixedWidth(320)
        self.text_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_input, alignment=Qt.AlignmentFlag.AlignCenter)

        self.keycap_display = KeycapDisplay()
        layout.addWidget(self.keycap_display, alignment=Qt.AlignmentFlag.AlignCenter)

        self._set_background("#f2f2f2")

    def _on_text_changed(self, text: str) -> None:
        self.keycap_display.set_text(text)

    def _randomize_background(self) -> None:
        # A "shade of green": fixed-ish green hue, randomized saturation/lightness.
        hue = random.randint(90, 140)
        saturation = random.randint(40, 90)
        lightness = random.randint(25, 70)
        self._set_background(f"hsl({hue}, {saturation}%, {lightness}%)")

    def _set_background(self, color: str) -> None:
        self._central.setStyleSheet(f"background-color: {color};")
