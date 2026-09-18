"""The left-hand region of the status bar: shows whatever's currently
hovered -- its keyboard shortcut, one keycap box per key, plus a short
explanation of what it does.

Purely presentational, like `TagPanel`/`TagRowDelegate`: it has no idea
what's hovering it or why, it just renders whatever `show_hint()` is
called with. `hover_hint.HoverHintController` (static widgets/actions) and
`MainWindow`'s tag-row hover handling (dynamic rows) are what call it.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget


class HoverExplainerBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("hoverExplainerBar")

        self._keys_layout = QHBoxLayout()
        self._keys_layout.setContentsMargins(0, 0, 0, 0)
        self._keys_layout.setSpacing(4)
        self._key_labels: list[QLabel] = []

        self._text_label = QLabel()
        self._text_label.setObjectName("hoverExplainerText")
        # Ignored (not Preferred) so this label is the one that gets
        # squeezed -- and its text clipped -- when the status bar's
        # permanent, fixed-size transient-message region on the right
        # needs more room than the two together have space for.
        self._text_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(8)
        layout.addLayout(self._keys_layout)
        layout.addWidget(self._text_label, 1)

    def show_hint(self, keys: tuple[str, ...], text: str) -> None:
        self._set_keys(keys)
        self._text_label.setText(text)

    def clear(self) -> None:
        self._set_keys(())
        self._text_label.setText("")

    def _set_keys(self, keys: tuple[str, ...]) -> None:
        while self._key_labels:
            label = self._key_labels.pop()
            self._keys_layout.removeWidget(label)
            label.deleteLater()
        for key in keys:
            label = QLabel(key)
            label.setObjectName("keycap")
            self._key_labels.append(label)
            self._keys_layout.addWidget(label)
