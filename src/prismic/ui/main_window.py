"""Main application window.

Everything above persistence goes through the Phase 3 application layer:
no widget here reads or writes the database or filesystem directly. Reads
go through repositories/queries; every mutation goes through
`PrismicSession.execute()`.
"""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path

from PySide6.QtCore import (
    QEvent,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSettings,
    Qt,
    QTimer,
)
from PySide6.QtGui import QAction, QCloseEvent, QKeyEvent, QKeySequence
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
from prismic.ui.hover_explainer_bar import HoverExplainerBar
from prismic.ui.hover_hint import HoverHintController
from prismic.ui.instance_bridge import InstanceBridge, request_focus
from prismic.ui.keyboard import KeyboardController
from prismic.ui.result_model import MediaIdRole, ResultListModel
from prismic.ui.tag_panel import TagPanel
from prismic.ui.thumbnail_delegate import ThumbnailDelegate
from prismic.ui.thumbnail_provider import ThumbnailProvider
from prismic.ui.transient_message_bar import TransientMessageBar
from prismic.ui.viewer import MediaViewer

_Index = QModelIndex | QPersistentModelIndex


class MainWindow(QMainWindow):
    def __init__(self, initial_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Prismic")
        self.resize(1280, 800)
        saved_geometry = QSettings().value("window/geometry")
        if saved_geometry is not None:
            self.restoreGeometry(saved_geometry)
        else:
            # No prior session to restore -- maximized is the sane default
            # rather than the arbitrary 1280x800 fallback size above.
            self.showMaximized()
        self.session: PrismicSession | None = None
        self._future_watchers: list[FutureWatcher] = []
        self._instance_bridge: InstanceBridge | None = None
        # Sticky last arrow-key direction, so preloading can bias further
        # ahead of travel than behind -- see _preload_neighbors().
        self._nav_direction = 1
        # See _stable_item_tags(): the item-tag panel's checked-group
        # ordering for whichever file is current, held stable across
        # add/remove until that file changes.
        self._item_tag_order: list[int] = []
        self._item_tag_order_item_id: int | None = None

        self._build_ui()
        self._build_status_bar()
        self._build_menu()

        self.keyboard = KeyboardController(
            on_navigate_previous=lambda: self._navigate(-1),
            on_navigate_next=lambda: self._navigate(1),
            on_undo=self._undo,
            on_focus_item_tags=self.item_tag_panel.focus_search,
            on_toggle_tag_by_index=self._toggle_tag_by_index,
            on_toggle_focus_mode=self._toggle_focus_mode,
            on_chord_status_changed=self._transient_bar.show_message,
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
        self._placeholder.setObjectName("emptyStateLabel")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Two independent tag lists rather than one dual-purpose one: the
        # top panel edits which tags are mapped to the file currently in
        # the viewer, the bottom narrows which files are browsable at all
        # (an intersection filter). Conflating "check to filter" and
        # "check to tag" into a single list would mean browsing could
        # silently mutate a file's tags -- kept deliberately separate.
        self.item_tag_panel = TagPanel("Edit this file")
        self.item_tag_panel.toggle_requested.connect(self._on_item_tag_toggle)
        self.item_tag_panel.create_and_check_requested.connect(self._on_item_create_and_check)
        self.item_tag_panel.rename_requested.connect(self._on_tag_rename)
        self.item_tag_panel.delete_requested.connect(self._on_tag_delete)
        self.item_tag_panel.hover_row_changed.connect(self._on_item_tag_hover)

        self.filter_panel = TagPanel("Filter")
        self.filter_panel.toggle_requested.connect(self._on_filter_toggle)
        self.filter_panel.create_and_check_requested.connect(self._on_filter_create_and_check)
        self.filter_panel.rename_requested.connect(self._on_tag_rename)
        self.filter_panel.delete_requested.connect(self._on_tag_delete)

        self._tag_splitter = QSplitter(Qt.Orientation.Vertical)
        self._tag_splitter.addWidget(self.item_tag_panel)
        self._tag_splitter.addWidget(self.filter_panel)
        self._tag_splitter.setSizes([1, 1])
        self._tag_splitter.setHandleWidth(1)

        self.thumbnail_provider = ThumbnailProvider(self)
        self.thumbnail_provider.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.thumbnail_provider.decode_failed.connect(self._on_thumbnail_ready)

        self.result_model = ResultListModel(self)
        self.result_list = QListView()
        self.result_list.setObjectName("resultList")
        # Never horizontal-scroll -- see TagPanel's matching setting for why.
        self.result_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.result_list.viewport().setMouseTracking(True)
        self.result_list.setModel(self.result_model)
        self._thumbnail_delegate = ThumbnailDelegate(
            self.thumbnail_provider,
            self._resolve_media_path,
            lambda: self.session.worker_pool if self.session is not None else None,
            self.result_list,
        )
        self.result_list.setItemDelegate(self._thumbnail_delegate)
        self.result_list.selectionModel().currentChanged.connect(self._on_result_selection_changed)

        self.viewer = MediaViewer(
            worker_pool=lambda: self.session.worker_pool if self.session is not None else None
        )
        self.viewer.load_error.connect(self._on_viewer_error)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._tag_splitter)
        splitter.addWidget(self.result_list)
        splitter.addWidget(self.viewer)
        splitter.setSizes([190, 260, 830])
        splitter.setHandleWidth(1)
        self._splitter = splitter

        self._central_stack = QStackedWidget()
        self._central_stack.addWidget(self._placeholder)
        self._central_stack.addWidget(self._splitter)
        self.setCentralWidget(self._central_stack)

    def _build_status_bar(self) -> None:
        self._hover_bar = HoverExplainerBar()
        self._transient_bar = TransientMessageBar()
        # Regular (non-permanent) widget: left-aligned, stretches to fill
        # whatever space the permanent widget on the right doesn't need --
        # see HoverExplainerBar's own size policy for what happens when
        # the two would otherwise overlap.
        self.statusBar().addWidget(self._hover_bar, 1)
        # Permanent: right-aligned, always visible -- this is what
        # replaces QStatusBar's own showMessage() area (see
        # TransientMessageBar's docstring).
        self.statusBar().addPermanentWidget(self._transient_bar)

        self._hover_hints = HoverHintController(self._hover_bar, self)
        self._hover_hints.register_widget(
            self.viewer.play_pause_button, ("Space",), "Play or pause the video"
        )
        self._hover_hints.register_widget(
            self.item_tag_panel.header, ("Tab",), "Cycle between edit and filter"
        )
        self._hover_hints.register_widget(
            self.filter_panel.header, ("Tab",), "Cycle between edit and filter"
        )

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_folder_action = file_menu.addAction(
            "Open Collection Folder…", self._prompt_open_folder
        )
        open_folder_action.setShortcut(QKeySequence("Ctrl+O"))
        self._hover_hints.register_action(
            open_folder_action, file_menu, ("Ctrl", "O"), "Open a folder as a collection"
        )

        open_file_action = file_menu.addAction("Open .prismic File…", self._prompt_open_file)
        open_file_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self._hover_hints.register_action(
            open_file_action,
            file_menu,
            ("Ctrl", "Shift", "O"),
            "Open an existing .prismic collection file",
        )

        file_menu.addSeparator()

        rescan_action = file_menu.addAction("Rescan", self._rescan)
        rescan_action.setShortcut(QKeySequence("Ctrl+R"))
        self._hover_hints.register_action(
            rescan_action, file_menu, ("Ctrl", "R"), "Rescan the collection folder for changes"
        )

        view_menu = self.menuBar().addMenu("&View")
        show_thumbnails_action = QAction("Show Thumbnails", self)
        show_thumbnails_action.setCheckable(True)
        show_thumbnails_action.setChecked(self._thumbnail_delegate.show_thumbnails)
        show_thumbnails_action.setShortcut(QKeySequence("Ctrl+T"))
        show_thumbnails_action.toggled.connect(self._on_toggle_thumbnails)
        view_menu.addAction(show_thumbnails_action)
        self._hover_hints.register_action(
            show_thumbnails_action,
            view_menu,
            ("Ctrl", "T"),
            "Toggle thumbnail previews in the results list",
        )

        self._focus_mode_action = QAction("Focus Mode", self)
        self._focus_mode_action.setCheckable(True)
        # No QKeySequence shortcut here on purpose -- Space is dispatched
        # through KeyboardController instead (see keyboard.py's module
        # docstring for why: a QShortcut here would collide with the
        # viewer's own Space-to-play/pause button shortcut and go
        # ambiguous -- silently firing neither -- whenever a video happens
        # to be showing).
        self._focus_mode_action.toggled.connect(self._apply_focus_mode)
        view_menu.addAction(self._focus_mode_action)
        self._hover_hints.register_action(
            self._focus_mode_action,
            view_menu,
            ("Space",),
            "Hide every panel except the media viewer",
        )

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
        self._focus_mode_action.setChecked(False)
        if self.session is not None:
            self.session.close()
            self.session = None
        if self._instance_bridge is not None:
            self._instance_bridge.release()
            self._instance_bridge = None
        self.thumbnail_provider.reset()

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
                self._transient_bar.show_message(
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
        # Two persistent QLineEdits (the tag search boxes) now live in the
        # main window's own widget tree rather than only inside transient
        # dialogs, so Qt's default initial-focus assignment on show() can
        # land on one of them instead of nothing in particular. The global
        # keyboard shortcuts deliberately stand down for *any* focused
        # QLineEdit (see eventFilter/_focus_is_text_editing) -- correct
        # while the user is actually typing a tag name, but it would
        # silently kill every shortcut from the moment a collection opens
        # if a search box just happened to inherit focus by default. Giving
        # the result list focus explicitly is what "immediately keyboard-
        # driven" actually requires here.
        self.result_list.setFocus()

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
        QSettings().setValue("window/geometry", self.saveGeometry())
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

    def _ordered_tags(self) -> list[Tag]:
        assert self.session is not None
        return self.session.tag_recency.order(self.session.tags.list_all())

    def _refresh_all(self) -> None:
        if self.session is None:
            return
        tags = self._ordered_tags()
        self.filter_panel.set_tags(tags, frozenset(self.session.state.selected_tag_ids))

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
            self.item_tag_panel.set_tags(tags, frozenset())
            self._item_tag_order = []
            self._item_tag_order_item_id = None
            return
        mapped_ids = frozenset(t.id for t in self.session.mappings.tags_for_media(current))
        self.item_tag_panel.set_tags(self._stable_item_tags(tags, mapped_ids, current), mapped_ids)

    def _stable_item_tags(
        self, tags: list[Tag], mapped_ids: frozenset[int], current_item: int
    ) -> list[Tag]:
        """Reorders `tags` so the checked (mapped-to-`current_item`) subset
        follows a stable, manually-maintained order instead of the
        popularity/recency algorithm: checking a tag appends it to the
        bottom of that group, unchecking one just drops it out -- neither
        perturbs where the rest sit. That stable order is only rebuilt from
        the algorithmic order when `current_item` differs from the last
        call, i.e. the panel is loading a different file."""
        if current_item != self._item_tag_order_item_id:
            self._item_tag_order = [t.id for t in tags if t.id in mapped_ids]
            self._item_tag_order_item_id = current_item
        else:
            self._item_tag_order = [tid for tid in self._item_tag_order if tid in mapped_ids]
            already_ordered = set(self._item_tag_order)
            self._item_tag_order += [
                t.id for t in tags if t.id in mapped_ids and t.id not in already_ordered
            ]

        by_id = {t.id: t for t in tags}
        stable_checked = [by_id[tid] for tid in self._item_tag_order if tid in by_id]
        rest = [t for t in tags if t.id not in mapped_ids]
        return stable_checked + rest

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
        self._preload_neighbors(current)

    def _preload_neighbors(self, current: int) -> None:
        """Warm the decode cache for the items around `current`, so
        arrow-key paging is usually a cache hit by the time the user
        actually lands on the next item.

        Biased two items ahead in `self._nav_direction` (the last arrow key
        pressed) and one behind: someone paging through a set of photos
        almost always keeps going the same way, including holding the key
        down or pressing it faster than one decode takes -- two-ahead is
        what keeps up with that, not just the single immediate neighbor.
        """
        assert self.session is not None
        result_set = self.session.state.result_set
        if current not in result_set:
            return
        index = result_set.index(current)
        root = self.session.collection.root
        ahead = self._nav_direction
        for offset in (ahead, 2 * ahead, -ahead):
            neighbor_index = index + offset
            if 0 <= neighbor_index < len(result_set):
                media = self.session.media.get(result_set[neighbor_index])
                if media is not None:
                    self.viewer.preload(root / media.relative_path)

    # -- User interaction -----------------------------------------------------

    def _on_result_selection_changed(self, current: _Index, _previous: _Index) -> None:
        if self.session is None or not current.isValid():
            return
        media_id = self.result_model.data(current, MediaIdRole)
        if not isinstance(media_id, int) or media_id == self.session.state.current_item:
            return
        self.session.state.current_item = media_id
        self._show_current_media()
        self._refresh_item_tag_panel(self._ordered_tags())

    def _navigate(self, delta: int) -> None:
        if self.session is None:
            return
        result_set = self.session.state.result_set
        if not result_set:
            return
        self._nav_direction = 1 if delta >= 0 else -1
        current = self.session.state.current_item
        if current is None or current not in result_set:
            new_index = 0
        else:
            index = result_set.index(current)
            new_index = max(0, min(len(result_set) - 1, index + delta))
        self.session.state.current_item = result_set[new_index]
        self._sync_result_selection()
        self._show_current_media()
        self._refresh_item_tag_panel(self._ordered_tags())

    def _undo(self) -> None:
        if self.session is None:
            return
        self.session.undo()
        self._refresh_all()

    def _on_filter_toggle(self, tag_id: int) -> None:
        if self.session is None:
            return
        self.session.tag_recency.record_click(tag_id)
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
        self.session.tag_recency.record_click(tag_id)
        mapped_ids = {t.id for t in self.session.mappings.tags_for_media(current)}
        if tag_id in mapped_ids:
            self.session.execute(MappingRemoveCommand(media_id=current, tag_id=tag_id))
        else:
            self.session.execute(MappingAddCommand(media_id=current, tag_id=tag_id))
        self._refresh_all()

    def _on_item_tag_hover(self, row: int | None) -> None:
        # Only rows 1-9 have a shortcut at all (the "t" then digit 1-9
        # chord below only covers that many) -- anything past that has
        # nothing to show yet, same as a row with no hover at all.
        if row is None or row >= 9:
            self._hover_bar.clear()
            return
        tag = self.item_tag_panel.model.tag_at(row)
        self._hover_bar.show_hint(("T", str(row + 1)), f'Toggle "{tag.name}" on the current item')

    def _on_item_create_and_check(self, name: str) -> None:
        tag = self._create_tag_and_find(name)
        if tag is not None:
            self._on_item_tag_toggle(tag.id)

    def _on_filter_create_and_check(self, name: str) -> None:
        tag = self._create_tag_and_find(name)
        if tag is not None:
            self._on_filter_toggle(tag.id)

    def _create_tag_and_find(self, name: str) -> Tag | None:
        """Creates a tag and returns it by name, for the search-box's
        "no match -> create it" flow, which needs the new tag's id to
        immediately apply/select it in the same keystroke. `TagCreateCommand`
        doesn't hand back the row it inserted, so this re-reads the tag list
        after creating -- names are unique, so the match is unambiguous."""
        if self.session is None:
            return None
        self._on_tag_create(name)
        for tag in self.session.tags.list_all():
            if tag.name == name:
                return tag
        return None  # creation failed (e.g. a duplicate name) -- _on_tag_create already warned

    def _on_toggle_thumbnails(self, checked: bool) -> None:
        self._thumbnail_delegate.show_thumbnails = checked
        # Row heights changed, which QListView doesn't pick up from a
        # repaint alone -- reset() forces it to re-query sizeHint for every
        # row. That also clears the view's own selection highlight, so the
        # current item's is restored right after.
        self.result_list.reset()
        self._sync_result_selection()

    def _toggle_focus_mode(self) -> None:
        self._focus_mode_action.setChecked(not self._focus_mode_action.isChecked())

    def _apply_focus_mode(self, checked: bool) -> None:
        """Hide (or restore) every panel except the media viewer itself.

        The viewer widget is left alone -- including its own video
        play/pause controls, which stay wherever they'd normally be. This
        only hides the browsing/tagging chrome around it: the tag panels,
        the result list, and the menu/status bars.
        """
        visible = not checked
        self._tag_splitter.setVisible(visible)
        self.result_list.setVisible(visible)
        self.menuBar().setVisible(visible)
        self.statusBar().setVisible(visible)

    def _toggle_tag_by_index(self, index: int) -> None:
        if self.session is None:
            return
        tags = self.session.tags.list_all()
        if not 0 <= index < len(tags):
            return
        self._on_item_tag_toggle(tags[index].id)

    def _on_viewer_error(self, reason: str) -> None:
        self._transient_bar.show_message(f"Could not load media: {reason}", 5000)

    def _resolve_media_path(self, media_id: int) -> Path | None:
        if self.session is None:
            return None
        media = self.session.media.get(media_id)
        if media is None:
            return None
        return self.session.collection.root / media.relative_path

    def _on_thumbnail_ready(self, media_id: int) -> None:
        row = self.result_model.row_for_media_id(media_id)
        if row is not None:
            self.result_list.update(self.result_model.index(row, 0))

    # -- Keyboard -------------------------------------------------------------

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key.Key_Escape:
                handled = False
                if self._focus_is_text_editing():
                    self._dismiss_typing_focus()
                    handled = True
                if self._focus_mode_action.isChecked():
                    # The reliable way out of focus mode -- Space alone
                    # can't be, since it's claimed by the viewer's own
                    # play/pause shortcut whenever a video is showing (see
                    # keyboard.py's module docstring).
                    self._focus_mode_action.setChecked(False)
                    handled = True
                if handled:
                    event.accept()
                    return True
            if event.key() == Qt.Key.Key_Tab and self._cycle_tag_search_focus():
                event.accept()
                return True
            if self.session is not None and self.keyboard.handle_key_press(
                event, text_editing=self._focus_is_text_editing()
            ):
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def _cycle_tag_search_focus(self) -> bool:
        """If focus is currently in one of the two tag search boxes, advance
        it around a 3-step loop: item-tag box -> filter box -> dismissed
        (back to the result list) -> item-tag box -> ... Report the key as
        handled for the first two steps; the third is a plain Tab-out, left
        to Qt's own focus handling instead of forced onto the result list,
        since the loop should end at "no longer typing," not at any one
        specific widget.

        Handled here, as a direct widget-identity check, rather than via
        `QWidget.setTabOrder`: Qt's tab-order chain is one single shared
        list for the whole window, and `setTabOrder(A, B)` only repositions
        a pair *within* it -- it can't carve out a closed loop excluding
        every other focusable widget, which is what "Tab between just these
        two boxes, then out" actually requires. Confirmed by trying it:
        `setTabOrder(A, B)` then `setTabOrder(B, A)` leaves A pointing at
        whatever followed B beforehand, not back at B."""
        focused = QApplication.focusWidget()
        if focused is self.item_tag_panel.search_box:
            self.filter_panel.search_box.setFocus()
            return True
        if focused is self.filter_panel.search_box:
            self._dismiss_typing_focus()
            return True
        return False

    def _dismiss_typing_focus(self) -> None:
        """Move focus off whatever text box currently has it and back to
        the result list -- the same "immediately keyboard-driven" default
        focus target `open_collection` sets on startup."""
        self.result_list.setFocus()

    @staticmethod
    def _focus_is_text_editing() -> bool:
        return isinstance(QApplication.focusWidget(), QLineEdit)
