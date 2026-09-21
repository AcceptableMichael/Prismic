"""The Settings window.

One panel so far -- Shortcuts -- but built as a sidebar-plus-stack rather
than a bare list, so a second panel is an `addWidget` and a list row
rather than a rewrite of the window around it.

The shortcut list is generated from `SHORTCUTS` in
`application/input/shortcuts.py`, in the order declared there, grouped by
that definition's own category. Nothing is enumerated by hand here, so a
shortcut added to the registry shows up in this window automatically and
one removed from it disappears -- there is no second list to forget to
update.

Purely presentational plus one piece of state (`ShortcutBindings`, which
persists itself). Nothing here touches a collection, a session, or the
database; `MainWindow` listens for `bindings_changed` and re-applies the
new keys to the live UI.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QMargins, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFocusEvent,
    QHideEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from prismic.application.input.shortcuts import (
    SHORTCUTS,
    ShortcutBindings,
    ShortcutDefinition,
    is_modifier_only,
    keycaps,
    normalize,
)
from prismic.application.input.shortcuts import (
    definition as shortcut_definition,
)
from prismic.ui import theme
from prismic.ui.keyboard import MODIFIER_KEY_NAMES, key_text

_UNSET_TEXT = "Not set"
_CAPTURING_TEXT = "Press a key…"


def binding_display(binding: str) -> str:
    """A binding as one human-readable string ("Ctrl + Shift + O").

    Spaced around the separator rather than Qt's tight "Ctrl+Shift+O": at
    the size these are rendered, an unspaced run of short tokens reads as
    one word. Built from `keycaps()` so it stays in step with how the
    hover-explainer bar splits the same string into boxes.

    A bare modifier gets spelled out, because "Ctrl" on its own would
    otherwise read as an unfinished combination rather than the tap
    gesture it actually is.
    """
    if is_modifier_only(binding):
        return f"{normalize(binding)} (tapped alone)"
    caps = keycaps(binding)
    return " + ".join(caps) if caps else _UNSET_TEXT


class KeyCaptureButton(QPushButton):
    """Click, then press the key combination to bind.

    While capturing, this widget has to win every key in the alphabet
    *including* the ones Qt normally spends on its own navigation: Tab
    would move focus, Space and Enter would re-activate this button,
    Escape would close the dialog. So capture is handled in `event()`
    ahead of Qt's own handling rather than in `keyPressEvent`, and
    `ShortcutOverride` is accepted too so a combination that matches some
    `QAction`'s shortcut is delivered here as an ordinary key press
    instead of firing that action.

    A modifier tapped on its own is a binding too, not a half-finished
    combination -- the release is what tells the two apart, so both are
    handled here. Every shortcut accepts one; see
    `shortcuts.is_modifier_only()` for what it then means.

    Escape is the one key that can't be bound this way, because it's the
    only way out of a capture the user didn't mean to start -- it cancels
    instead. That doesn't make Escape unbindable in general: it's the
    default for Dismiss, and a shortcut that's been moved off Escape can
    be put back with the row's own Reset button.
    """

    binding_captured = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("shortcutCaptureButton")
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._binding = ""
        # A modifier that has gone down with nothing else since. Its
        # release is what turns it into a binding -- see `event()`.
        self._pending_modifier: int | None = None
        self.clicked.connect(self._on_clicked)

    @property
    def is_capturing(self) -> bool:
        return self.isChecked()

    def set_binding(self, binding: str) -> None:
        self._binding = binding
        self._refresh_text()

    def _refresh_text(self) -> None:
        if self.is_capturing:
            self.setText(_CAPTURING_TEXT)
        else:
            self.setText(binding_display(self._binding))
        # Styled from the property rather than an inline stylesheet, so
        # the whole look stays in theme.py with everything else.
        self.setProperty("unset", not self._binding and not self.is_capturing)
        style = self.style()
        style.unpolish(self)
        style.polish(self)

    def _on_clicked(self) -> None:
        self._refresh_text()
        if self.is_capturing:
            self.grabKeyboard()
        else:
            self.releaseKeyboard()

    def _stop_capturing(self) -> None:
        if self.is_capturing:
            self.releaseKeyboard()
            self.setChecked(False)
            self._refresh_text()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        # Clicking elsewhere (or tabbing away, which only happens once
        # capture has already ended) abandons a capture rather than
        # leaving an invisible one armed on an unfocused widget.
        self._stop_capturing()
        super().focusOutEvent(event)

    def hideEvent(self, event: QHideEvent) -> None:
        # `grabKeyboard()` is an application-wide grab: while it's held,
        # every key event in the process comes here regardless of what
        # the user thinks they're typing into. Losing focus is the usual
        # way out (above), but closing the Settings window with a capture
        # still armed doesn't necessarily deliver a focus-out first --
        # and a grab held by a hidden, or since-destroyed, widget would
        # take the keyboard away from the whole app with nothing on
        # screen to explain why.
        self._stop_capturing()
        super().hideEvent(event)

    def event(self, event: QEvent) -> bool:
        if not self.is_capturing or not isinstance(event, QKeyEvent):
            return super().event(event)
        if event.type() == QEvent.Type.ShortcutOverride:
            event.accept()
            return True
        if event.type() == QEvent.Type.KeyRelease:
            return self._handle_release(event)
        if event.type() != QEvent.Type.KeyPress:
            return super().event(event)
        if event.key() == Qt.Key.Key_Escape:
            self._stop_capturing()
            return True
        if not event.isAutoRepeat():
            if self._pending_modifier is not None:
                # Something else went down while a modifier was held, so
                # it's a combination now, not a tap.
                self._pending_modifier = None
            elif event.key() in MODIFIER_KEY_NAMES:
                self._pending_modifier = event.key()
        captured = key_text(event)
        if captured is None:
            # A bare modifier. It could still become a combination (the
            # user is mid-chord) or end as a tap -- its release decides.
            return True
        self._pending_modifier = None
        self._stop_capturing()
        self.binding_captured.emit(captured)
        return True

    def _handle_release(self, event: QKeyEvent) -> bool:
        """A modifier let go with nothing pressed since it went down is a
        tap, and taps are bindable like any other input -- that's how the
        Edit list's numbering swap gets its default of plain Ctrl. Every
        other release is swallowed, since the press it belongs to was
        already dealt with above."""
        pending = self._pending_modifier
        if pending is None or event.isAutoRepeat() or event.key() != pending:
            return True
        self._pending_modifier = None
        self._stop_capturing()
        self.binding_captured.emit(MODIFIER_KEY_NAMES[pending])
        return True


class ShortcutRow(QWidget):
    """One shortcut: what it does on the left, what it's bound to on the
    right, and the two buttons for unbinding it and putting it back."""

    changed = Signal()

    def __init__(
        self,
        definition: ShortcutDefinition,
        bindings: ShortcutBindings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("shortcutRow")
        self.definition = definition
        self._bindings = bindings

        self._label = QLabel(definition.label)
        self._label.setObjectName("shortcutLabel")
        self._description = QLabel(definition.description)
        self._description.setObjectName("shortcutDescription")
        self._description.setWordWrap(True)
        self._conflict = QLabel()
        self._conflict.setObjectName("shortcutConflict")
        self._conflict.setWordWrap(True)
        self._conflict.setVisible(False)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(2)
        text_column.addWidget(self._label)
        text_column.addWidget(self._description)
        text_column.addWidget(self._conflict)

        # One editor for every shortcut, with no per-command variations:
        # whether a binding turns out to be a key, a combination or a
        # bare modifier tap is decided by what the user presses into it,
        # not by anything the registry says about the command.
        self._editor = KeyCaptureButton(self)
        self._editor.binding_captured.connect(self._assign)
        self._editor.setFixedWidth(180)

        self._clear_button = QPushButton("Clear", self)
        self._clear_button.setObjectName("shortcutSmallButton")
        self._clear_button.clicked.connect(lambda: self._assign(""))
        self._reset_button = QPushButton("Reset", self)
        self._reset_button.setObjectName("shortcutSmallButton")
        self._reset_button.clicked.connect(self._reset)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        layout.addLayout(text_column, 1)
        layout.addWidget(self._editor)
        layout.addWidget(self._clear_button)
        layout.addWidget(self._reset_button)

        self.refresh()

    def matches(self, query: str) -> bool:
        """Whether this row survives the panel's search box. Matching on
        the binding too means "what's on Ctrl+T again?" is answerable by
        typing the key, not just the feature's name."""
        query = query.strip().lower()
        if not query:
            return True
        haystack = " ".join(
            (
                self.definition.label,
                self.definition.description,
                self.definition.category,
                binding_display(self._bindings.binding(self.definition.id)),
            )
        ).lower()
        return query in haystack

    def refresh(self) -> None:
        binding = self._bindings.binding(self.definition.id)
        self._editor.set_binding(binding)
        self._clear_button.setEnabled(bool(binding))
        self._reset_button.setEnabled(not self._bindings.is_default(self.definition.id))
        conflicts = self._bindings.conflicts(self.definition.id, binding)
        if conflicts:
            names = ", ".join(shortcut_definition(other).label for other in conflicts)
            self._conflict.setText(f"Also bound to: {names}")
            self._conflict.setVisible(True)
        else:
            self._conflict.setVisible(False)

    def _assign(self, binding: str) -> None:
        current = self._bindings.binding(self.definition.id)
        if binding == current:
            self.refresh()
            return
        if binding and not self._confirm_conflicts(binding):
            self.refresh()
            return
        self._bindings.set_binding(self.definition.id, binding)
        self.changed.emit()

    def _confirm_conflicts(self, binding: str) -> bool:
        """Ask before taking a key off whatever else is using it.

        Returns False if the user backs out, leaving both shortcuts as
        they were. Only same-scope collisions are asked about -- see
        `ShortcutScope` for why Space on both Focus Mode and the viewer's
        play/pause is not one."""
        conflicts = self._bindings.conflicts(self.definition.id, binding)
        if not conflicts:
            return True
        names = ", ".join(shortcut_definition(other).label for other in conflicts)
        answer = QMessageBox.question(
            self,
            "Shortcut already in use",
            f"{binding_display(binding)} is already bound to {names}.\n\n"
            f"Assign it to “{self.definition.label}” and clear the other?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        for other in conflicts:
            self._bindings.set_binding(other, "")
        return True

    def _reset(self) -> None:
        self._bindings.reset(self.definition.id)
        self.changed.emit()


class ShortcutsPanel(QWidget):
    """Every shortcut in the app, grouped by category, each editable."""

    changed = Signal()

    def __init__(self, bindings: ShortcutBindings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bindings = bindings

        self._search_box = QLineEdit(self)
        self._search_box.setObjectName("settingsSearchBox")
        self._search_box.setPlaceholderText("Search shortcuts…")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.textChanged.connect(self._apply_search)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(0)

        self.rows: list[ShortcutRow] = []
        self._headers: dict[str, QLabel] = {}
        self._separators_by_row: dict[ShortcutRow, QFrame] = {}
        current_category: str | None = None
        for definition in SHORTCUTS:
            if definition.category != current_category:
                current_category = definition.category
                header = QLabel(current_category.upper())
                header.setObjectName("panelTitle")
                content_layout.addWidget(header)
                self._headers[current_category] = header
            row = ShortcutRow(definition, bindings, content)
            row.changed.connect(self._on_row_changed)
            content_layout.addWidget(row)
            self.rows.append(row)
            separator = QFrame(content)
            separator.setObjectName("rowSeparator")
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFixedHeight(1)
            content_layout.addWidget(separator)
            self._separators_by_row[row] = separator
        content_layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Never horizontal-scroll, for the same reason `TagPanel` and the
        # result list don't: every row fits the viewport by construction
        # (the descriptions wrap, the editors are fixed-width), so a
        # horizontal scrollbar here is only ever Qt reacting to a
        # transient width miscalculation, not to anything actually cut
        # off. Left on the default policy it does exactly that -- on the
        # first layout pass, before the vertical scrollbar's width has
        # been taken out of the viewport, the content is momentarily too
        # wide and a horizontal bar appears for one frame and then goes
        # away again. That one frame is a visible flash when the window
        # opens.
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)

        self._restore_button = QPushButton("Restore all defaults", self)
        self._restore_button.clicked.connect(self._restore_defaults)
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addWidget(self._restore_button)
        footer.addStretch(1)

        self._empty_label = QLabel("No shortcuts match that search.")
        self._empty_label.setObjectName("emptyStateLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self._search_box)
        layout.addWidget(self._empty_label)
        layout.addWidget(scroll, 1)
        layout.addLayout(footer)

    @property
    def search_box(self) -> QLineEdit:
        return self._search_box

    def visible_rows(self) -> list[ShortcutRow]:
        return [row for row in self.rows if row.isVisibleTo(self)]

    def _apply_search(self) -> None:
        query = self._search_box.text()
        shown_by_category: dict[str, int] = dict.fromkeys(self._headers, 0)
        for row in self.rows:
            visible = row.matches(query)
            row.setVisible(visible)
            self._separators_by_row[row].setVisible(visible)
            if visible:
                shown_by_category[row.definition.category] += 1
        for category, header in self._headers.items():
            header.setVisible(shown_by_category[category] > 0)
        self._empty_label.setVisible(not any(shown_by_category.values()))

    def _on_row_changed(self) -> None:
        # Every row, not just the edited one: taking a key away from
        # another shortcut (or restoring a default that collides with
        # one) changes what those rows should be showing too.
        self.refresh()
        self.changed.emit()

    def refresh(self) -> None:
        for row in self.rows:
            row.refresh()

    def _restore_defaults(self) -> None:
        answer = QMessageBox.question(
            self,
            "Restore default shortcuts",
            "Put every shortcut back to its default key?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._bindings.reset_all()
        self._on_row_changed()


class TitleBar(QWidget):
    """The window's own title strip, standing in for the native one.

    The dialog is frameless (see `SettingsDialog`), so the two things a
    title bar is actually load-bearing for have to be provided here:
    somewhere to grab the window by, and a way to close it.

    Dragging is handed to `QWindow::startSystemMove()` rather than
    tracked by hand from mouse deltas. It asks the window manager to run
    its own move loop, which is what keeps edge snapping, multi-monitor
    boundaries and per-monitor DPI working -- all things a manual
    "remember the press offset and call move()" implementation quietly
    gets wrong, and which are the reason hand-rolled title bars tend to
    feel slightly off.
    """

    close_requested = Signal()

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsTitleBar")

        self._label = QLabel(title, self)
        self._label.setObjectName("settingsTitle")

        self.close_button = QPushButton("✕", self)
        self.close_button.setObjectName("windowCloseButton")
        # Never the dialog's default button: Return belongs to whatever
        # the user is actually working in, not to closing the window.
        self.close_button.setAutoDefault(False)
        self.close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_button.clicked.connect(self.close_requested)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._label)
        layout.addStretch(1)
        layout.addWidget(self.close_button)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        # Deliberately swallowed. On a native title bar a double-click
        # maximizes, which for a fixed-purpose settings window is never
        # what's wanted -- and without the native frame there'd be no
        # obvious way back out of it.
        event.accept()


class SizeGrip(QSizeGrip):
    """A resize corner that's actually visible.

    `QSizeGrip` leaves its own painting to the platform style, and this
    app's stylesheet sets a background on every `QWidget` -- which wins,
    blanking the style's diagonal lines and leaving a working but
    completely invisible handle. Drawing it here is the same approach
    `TagRowDelegate` takes for its row icons: paint it rather than hope
    the style survives the QSS.

    Resizing itself is still `QSizeGrip`'s; only the pixels are ours.
    """

    _SIZE = 16

    def __init__(self, parent: QWidget) -> None:
        # Required, not optional, unlike the other widgets here:
        # QSizeGrip resizes *its window*, so one without a parent has
        # nothing to act on.
        super().__init__(parent)
        self.setFixedSize(self._SIZE, self._SIZE)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(theme.TEXT_MUTED), 1.4))
        # Three diagonals of increasing length toward the corner -- the
        # conventional grip, so it needs no explaining.
        for offset in (3, 7, 11):
            painter.drawLine(
                self._SIZE - 2, self._SIZE - offset, self._SIZE - offset, self._SIZE - 2
            )


class SettingsDialog(QDialog):
    bindings_changed = Signal()

    def __init__(self, bindings: ShortcutBindings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setObjectName("settingsDialog")
        self.setModal(True)
        # No native title bar, icon or close button: this window is all
        # app-themed surfaces, and a light OS frame around them read as
        # a different program's window sitting on top. `TitleBar` below
        # supplies what the native frame was actually for. Set before
        # `_center_on_parent()` calls `create()`, since changing window
        # flags after the native window exists destroys and recreates it.
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.resize(760, 620)

        self.shortcuts_panel = ShortcutsPanel(bindings, self)
        self.shortcuts_panel.changed.connect(self.bindings_changed)

        self.panel_list = QListWidget(self)
        self.panel_list.setObjectName("settingsPanelList")
        self.panel_list.addItem("Shortcuts")
        self.panel_list.setCurrentRow(0)
        self.panel_list.setFixedWidth(150)
        self.panel_list.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self.shortcuts_panel)
        self.panel_list.currentRowChanged.connect(self._stack.setCurrentIndex)

        self.title_bar = TitleBar("Settings", self)
        self.title_bar.close_requested.connect(self.accept)

        close_button = QPushButton("Close", self)
        close_button.setDefault(True)
        close_button.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(close_button)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.panel_list)
        body.addWidget(self._stack, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.title_bar)
        layout.addLayout(body, 1)
        footer_widget = QWidget(self)
        footer_widget.setObjectName("settingsFooter")
        footer_widget.setLayout(footer)
        layout.addWidget(footer_widget)

        # Frameless windows lose the native resize borders along with the
        # rest of the frame, and this list is long enough that being able
        # to make the window taller genuinely matters. Parented to the
        # dialog and positioned in `resizeEvent` rather than put in the
        # footer layout, so it sits flush in the corner the way a resize
        # handle is expected to -- inside the footer it would be inset by
        # that widget's padding, floating oddly short of the edge.
        self._size_grip = SizeGrip(self)

        self._center_on_parent()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        grip = self._size_grip
        # One pixel in from each edge, clearing the window's own border.
        grip.move(self.width() - grip.width() - 1, self.height() - grip.height() - 1)
        grip.raise_()

    def _center_on_parent(self) -> None:
        """Place the window over its parent before it is ever shown.

        Not cosmetic bookkeeping -- this is what stops a visible flash on
        open. Left to itself, `QDialog::adjustPosition()` runs *twice*:
        once before the window is mapped, when the frame margins aren't
        known yet and count as zero, and again once they are. So the
        dialog appears at one position and then jumps by the size of its
        own title bar and border, on the frame *after* it became visible.
        Measured here as a (-10, -10) `Move` arriving after `Show`, with
        the first `Paint` only afterwards.

        Calling `move()` at all sets `Qt::WA_Moved`, which is the flag
        `adjustPosition()` checks before doing anything -- so positioning
        it once, ourselves, replaces the two-step entirely.

        `create()` is what makes that a fair trade rather than swapping a
        flash for a misplaced window: it builds the native window without
        showing it, which is the point at which the frame margins become
        real (0/30/0/0 on Windows 11 -- a title bar and no border). With
        them in hand we can centre the *frame*, which is what Qt's second
        pass was for, while still doing it entirely before the window is
        on screen.
        """
        parent = self.parentWidget()
        if parent is None:
            return  # a parentless dialog is the platform's to place
        self.create()
        handle = self.windowHandle()
        margins = handle.frameMargins() if handle is not None else QMargins()

        frame = QRect(
            QPoint(),
            QSize(
                self.width() + margins.left() + margins.right(),
                self.height() + margins.top() + margins.bottom(),
            ),
        )
        frame.moveCenter(parent.window().frameGeometry().center())

        screen = parent.window().screen()
        if screen is not None:
            # The same clamp Qt applies, for when the main window is
            # itself partly off-screen -- without it, centring on that
            # window would put this one's title bar out of reach.
            available = screen.availableGeometry()
            frame.moveLeft(
                max(available.left(), min(frame.left(), available.right() - frame.width()))
            )
            frame.moveTop(
                max(available.top(), min(frame.top(), available.bottom() - frame.height()))
            )

        self.move(frame.left() + margins.left(), frame.top() + margins.top())
