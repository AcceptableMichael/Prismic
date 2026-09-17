"""Main application window.

Everything above persistence goes through the Phase 3 application layer:
no widget here reads or writes the database or filesystem directly. Reads
go through repositories/queries; every mutation goes through
`PrismicSession.execute()`.
"""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path

from PySide6.QtCore import QEvent, QModelIndex, QObject, QPersistentModelIndex, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from prismic.application.commands.filter_commands import (
    FilterDeselectCommand,
    FilterSelectCommand,
)
from prismic.application.commands.mapping_commands import MappingAddCommand, MappingRemoveCommand
from prismic.application.commands.tag_commands import (
    TagCreateCommand,
    TagDeleteCommand,
    TagRenameCommand,
)
from prismic.application.queries.media_query import eligible_media
from prismic.application.session import PrismicSession
from prismic.domain.tag import Tag
from prismic.indexing.reconciler import ReconciliationResult
from prismic.persistence.errors import CollectionLockedError, PersistenceError
from prismic.ui.future_watcher import FutureWatcher
from prismic.ui.instance_bridge import InstanceBridge, request_focus
from prismic.ui.keyboard import KeyboardController
from prismic.ui.result_model import MediaIdRole, ResultListModel
from prismic.ui.tag_panel import TagPanel
from prismic.ui.viewer import MediaViewer

_Index = QModelIndex | QPersistentModelIndex


class MainWindow(QMainWindow):
    def __init__(self, initial_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Prismic")
        self.resize(1280, 800)
        self.session: PrismicSession | None = None
        self._future_watchers: list[FutureWatcher] = []
        self._instance_bridge: InstanceBridge | None = None

        self._build_ui()
        self._build_menu()

        self.keyboard = KeyboardController(
            on_navigate_previous=lambda: self._navigate(-1),
            on_navigate_next=lambda: self._navigate(1),
            on_undo=self._undo,
            on_create_tag=self.filter_panel.prompt_new_tag,
            on_toggle_tag_by_index=self._toggle_tag_by_index,
            on_chord_status_changed=self.statusBar().showMessage,
            parent=self,
        )
        # Installed on the application, not just this window: a normal Qt
        # keyPressEvent override only fires when *this widget* has focus,
        # but Qt delivers key events to whatever child widget is focused
        # first -- and QAbstractItemView (the tag/result lists) has its own
        # built-in "type to search" behavior that swallows plain letter/
        # digit keys before they'd ever reach here. Global commands and
        # chords need to win regardless of which child last had a click, so
        # they're intercepted at the application level instead. Text-editing
        # widgets (a QLineEdit inside a rename/create dialog) are explicitly
        # exempted -- that's this app's actual TEXT_EDITING precedence case.
        app = QApplication.instance()
        assert app is not None  # a QApplication always exists by the time a QWidget is built
        app.installEventFilter(self)

        if initial_path is not None:
            # Deferred to the next event-loop iteration rather than opened
            # right here: the caller (bootstrap.run()) calls `.show()`
            # immediately after constructing this window, before starting
            # the event loop -- opening synchronously in __init__ meant a
            # "collection already open elsewhere" QMessageBox could pop up
            # against a window that was never actually shown yet, then an
            # empty placeholder window would appear only *after* the
            # dialog was dismissed. A zero-delay QTimer runs after `.show()`
            # has taken effect, so the window is visibly there first and
            # any error dialog reads as "this window couldn't open X"
            # rather than appearing to come from nowhere.
            QTimer.singleShot(0, lambda: self.open_collection(initial_path, is_startup=True))

    def _build_ui(self) -> None:
        self._placeholder = QLabel("No collection open")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.filter_panel = TagPanel("Tags (filter)", editable=True)
        self.filter_panel.toggle_requested.connect(self._on_filter_toggle)
        self.filter_panel.create_requested.connect(self._on_tag_create)
        self.filter_panel.rename_requested.connect(self._on_tag_rename)
        self.filter_panel.delete_requested.connect(self._on_tag_delete)

        self.item_tag_panel = TagPanel("Tags on this item", editable=False)
        self.item_tag_panel.toggle_requested.connect(self._on_item_tag_toggle)

        self.result_model = ResultListModel(self)
        self.result_list = QListView()
        self.result_list.setModel(self.result_model)
        self.result_list.selectionModel().currentChanged.connect(self._on_result_selection_changed)

        self.viewer = MediaViewer()
        self.viewer.load_error.connect(self._on_viewer_error)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.filter_panel)
        splitter.addWidget(self.result_list)

        right_side = QWidget()
        right_layout = QVBoxLayout(right_side)
        right_layout.addWidget(self.viewer, 1)
        right_layout.addWidget(self.item_tag_panel)
        splitter.addWidget(right_side)
        splitter.setSizes([220, 320, 640])
        self._splitter = splitter

        self._central_stack = QStackedWidget()
        self._central_stack.addWidget(self._placeholder)
        self._central_stack.addWidget(self._splitter)
        self.setCentralWidget(self._central_stack)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("Open Collection Folder…", self._prompt_open_folder)
        file_menu.addAction("Open .prismic File…", self._prompt_open_file)
        file_menu.addSeparator()
        file_menu.addAction("Rescan", self._rescan)

    # -- Session lifecycle --------------------------------------------------

    def _prompt_open_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Open Collection Folder")
        if directory:
            self.open_collection(Path(directory))

    def _prompt_open_file(self) -> None:
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self, "Open .prismic File", filter="Prismic Collection (*.prismic)"
        )
        if file_path:
            self.open_collection(Path(file_path))

    def open_collection(self, path: Path, *, is_startup: bool = False) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None
        if self._instance_bridge is not None:
            self._instance_bridge.release()
            self._instance_bridge = None

        try:
            session = PrismicSession.open(path)
        except CollectionLockedError as exc:
            # The file lock is authoritative; this is just a best-effort
            # nicety on top of it. If another running instance is
            # reachable, ask it to raise itself instead of showing a plain
            # error -- and if this attempt was the CLI startup launch (the
            # OS double-click case), there's nothing else for this second
            # process to do, so it quits rather than leaving an empty
            # window behind.
            if request_focus(exc.path):
                if is_startup:
                    self.close()
                    return
                self.statusBar().showMessage(
                    "That collection is already open — brought its window to the front.",
                    5000,
                )
            else:
                QMessageBox.critical(self, "Could not open collection", str(exc))
            self._central_stack.setCurrentWidget(self._placeholder)
            return
        except PersistenceError as exc:
            QMessageBox.critical(self, "Could not open collection", str(exc))
            self._central_stack.setCurrentWidget(self._placeholder)
            return

        self.session = session
        self._instance_bridge = InstanceBridge(self)
        self._instance_bridge.raise_requested.connect(self._on_raise_requested)
        self._instance_bridge.take_ownership(session.collection.database_path)
        self.setWindowTitle(f"Prismic — {session.collection.root.name}")
        self._central_stack.setCurrentWidget(self._splitter)
        self._watch_reconciliation(session.initial_reconciliation)
        self._refresh_all()

    def _on_raise_requested(self) -> None:
        self.setWindowState(
            (self.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive
        )
        self.show()
        self.raise_()
        self.activateWindow()
        # Belt and braces: OS-level focus-stealing prevention (the same
        # mechanism documented in project guidance.md for this app's own
        # window at launch) can silently deny activateWindow() when this
        # process isn't already the foreground one -- observed live, not
        # just theorized. QApplication.alert() is the OS-sanctioned "ask
        # for attention" request (taskbar flash on Windows, dock bounce on
        # macOS) that works even when activation itself is denied.
        QApplication.alert(self)

    def _rescan(self) -> None:
        if self.session is None:
            return
        self._watch_reconciliation(self.session.rescan())

    def _watch_reconciliation(self, future: Future[ReconciliationResult]) -> None:
        watcher = FutureWatcher(future, self)
        watcher.finished.connect(self._on_reconciliation_finished)
        self._future_watchers.append(watcher)

    def _on_reconciliation_finished(self, _result: object) -> None:
        if self.session is None:
            return
        self.session.refresh_state()
        self._refresh_all()

    def closeEvent(self, event: QCloseEvent) -> None:
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        if self._instance_bridge is not None:
            self._instance_bridge.release()
            self._instance_bridge = None
        if self.session is not None:
            self.session.close()
            self.session = None
        super().closeEvent(event)

    # -- Refreshing the UI from session state --------------------------------

    def _refresh_all(self) -> None:
        if self.session is None:
            return
        tags = self.session.tags.list_all()
        self.filter_panel.model.set_tags(tags, frozenset(self.session.state.selected_tag_ids))

        media_list = eligible_media(
            self.session.media, self.session.mappings, self.session.state.selected_tag_ids
        )
        self.result_model.set_media(media_list)

        self._sync_result_selection()
        self._show_current_media()
        self._refresh_item_tag_panel(tags)

    def _refresh_item_tag_panel(self, tags: list[Tag]) -> None:
        assert self.session is not None
        current = self.session.state.current_item
        if current is None:
            self.item_tag_panel.model.set_tags(tags, frozenset())
            return
        mapped_ids = frozenset(t.id for t in self.session.mappings.tags_for_media(current))
        self.item_tag_panel.model.set_tags(tags, mapped_ids)

    def _sync_result_selection(self) -> None:
        assert self.session is not None
        current = self.session.state.current_item
        if current is None:
            self.result_list.clearSelection()
            return
        row = self.result_model.row_for_media_id(current)
        if row is not None:
            self.result_list.setCurrentIndex(self.result_model.index(row, 0))

    def _show_current_media(self) -> None:
        assert self.session is not None
        current = self.session.state.current_item
        if current is None:
            self.viewer.clear()
            return
        media = self.session.media.get(current)
        if media is None:
            self.viewer.clear()
            return
        self.viewer.show_media(self.session.collection.root / media.relative_path)

    # -- User interaction -----------------------------------------------------

    def _on_result_selection_changed(self, current: _Index, _previous: _Index) -> None:
        if self.session is None or not current.isValid():
            return
        media_id = self.result_model.data(current, MediaIdRole)
        if not isinstance(media_id, int) or media_id == self.session.state.current_item:
            return
        self.session.state.current_item = media_id
        self._show_current_media()
        self._refresh_item_tag_panel(self.session.tags.list_all())

    def _navigate(self, delta: int) -> None:
        if self.session is None:
            return
        result_set = self.session.state.result_set
        if not result_set:
            return
        current = self.session.state.current_item
        if current is None or current not in result_set:
            new_index = 0
        else:
            index = result_set.index(current)
            new_index = max(0, min(len(result_set) - 1, index + delta))
        self.session.state.current_item = result_set[new_index]
        self._sync_result_selection()
        self._show_current_media()
        self._refresh_item_tag_panel(self.session.tags.list_all())

    def _undo(self) -> None:
        if self.session is None:
            return
        self.session.undo()
        self._refresh_all()

    def _on_filter_toggle(self, tag_id: int) -> None:
        if self.session is None:
            return
        if tag_id in self.session.state.selected_tag_ids:
            self.session.execute(FilterDeselectCommand(tag_id=tag_id))
        else:
            self.session.execute(FilterSelectCommand(tag_id=tag_id))
        self._refresh_all()

    def _on_tag_create(self, name: str) -> None:
        if self.session is None:
            return
        try:
            self.session.execute(TagCreateCommand(name=name))
        except Exception as exc:  # noqa: BLE001 - shown to the user, not swallowed
            QMessageBox.warning(self, "Could not create tag", str(exc))
        self._refresh_all()

    def _on_tag_rename(self, tag_id: int, new_name: str) -> None:
        if self.session is None:
            return
        try:
            self.session.execute(TagRenameCommand(tag_id=tag_id, new_name=new_name))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Could not rename tag", str(exc))
        self._refresh_all()

    def _on_tag_delete(self, tag_id: int) -> None:
        if self.session is None:
            return
        self.session.execute(TagDeleteCommand(tag_id=tag_id))
        self._refresh_all()

    def _on_item_tag_toggle(self, tag_id: int) -> None:
        if self.session is None:
            return
        current = self.session.state.current_item
        if current is None:
            return
        mapped_ids = {t.id for t in self.session.mappings.tags_for_media(current)}
        if tag_id in mapped_ids:
            self.session.execute(MappingRemoveCommand(media_id=current, tag_id=tag_id))
        else:
            self.session.execute(MappingAddCommand(media_id=current, tag_id=tag_id))
        self._refresh_all()

    def _toggle_tag_by_index(self, index: int) -> None:
        if self.session is None:
            return
        tags = self.session.tags.list_all()
        if not 0 <= index < len(tags):
            return
        self._on_item_tag_toggle(tags[index].id)

    def _on_viewer_error(self, reason: str) -> None:
        self.statusBar().showMessage(f"Could not load media: {reason}", 5000)

    # -- Keyboard -------------------------------------------------------------

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            event.type() == QEvent.Type.KeyPress
            and self.session is not None
            and not self._focus_is_text_editing()
            and isinstance(event, QKeyEvent)
            and self.keyboard.handle_key_press(event)
        ):
            event.accept()
            return True
        return super().eventFilter(watched, event)

    @staticmethod
    def _focus_is_text_editing() -> bool:
        return isinstance(QApplication.focusWidget(), QLineEdit)
