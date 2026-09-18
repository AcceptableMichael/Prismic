"""A titled tag list: a search-to-filter-or-create box on top, a list of
tag rows below.

Checked tags are always sorted to the top, so what's already applied (or,
for the filter panel, already active) reads at a glance; typing in the
search box narrows only the *unchecked* tags beneath them, leaving the
checked ones pinned in place. Hitting Enter toggles on the top-filtered
match, or -- if nothing matches -- asks the caller to create a tag with
that name and immediately check it, so a single keystroke-driven flow
covers both "find and apply" and "create and apply" without a dialog.

Row interaction itself (whole-row toggle, hover rename/delete icons,
inline rename) lives in `TagRowDelegate`; this widget only wires its
signals through and owns the search/filter bookkeeping. Purely a
presentation shell around `TagListModel` -- every user action comes out
as a Qt signal; nothing here calls into the application layer directly
(see `main_window.py`, which dispatches commands).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QHoverEvent, QMouseEvent
from PySide6.QtWidgets import QLabel, QLineEdit, QListView, QVBoxLayout, QWidget

from prismic.domain.tag import Tag
from prismic.ui.tag_model import TagListModel
from prismic.ui.tag_row_delegate import TagRowDelegate


class TagPanel(QWidget):
    toggle_requested = Signal(int)  # tag_id
    create_and_check_requested = Signal(str)  # name -- create the tag, then apply/select it
    rename_requested = Signal(int, str)  # tag_id, new_name
    delete_requested = Signal(int)  # tag_id
    hover_row_changed = Signal(object)  # int row index, or None when hovering no row

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tags: list[Tag] = []
        self._checked_ids: frozenset[int] = frozenset()

        self.model = TagListModel(self)

        self.search_box = QLineEdit(self)
        self.search_box.setObjectName("tagSearchBox")
        self.search_box.setPlaceholderText("Search or create…")
        self.search_box.textChanged.connect(self._apply_filter)
        self.search_box.returnPressed.connect(self._commit_search)

        self.list_view = QListView(self)
        self.list_view.setObjectName("tagList")
        # Never horizontal-scroll: a row's own text elides to fit instead
        # (TagRowDelegate), so a horizontal scrollbar here would only ever
        # be Qt reacting to a sub-pixel width miscalculation, not anything
        # actually cut off.
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_view.viewport().setMouseTracking(True)
        self.list_view.viewport().installEventFilter(self)
        self.list_view.setModel(self.model)
        delegate = TagRowDelegate(self.list_view, self.list_view)
        delegate.toggle_requested.connect(self.toggle_requested)
        delegate.delete_requested.connect(self.delete_requested)
        delegate.rename_committed.connect(self.rename_requested)
        self.list_view.setItemDelegate(delegate)

        title_label = QLabel(title.upper())
        title_label.setObjectName("panelTitle")

        # Title + search box grouped into one widget so the hover-explainer
        # (see HoverHintController in main_window.py) can treat them as a
        # single hoverable target for this panel's focus shortcut, rather
        # than just the search box itself.
        self.header = QWidget(self)
        self.header.setObjectName("tagPanelHeader")
        header_layout = QVBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_layout.addWidget(title_label)
        header_layout.addWidget(self.search_box)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.list_view, 1)

    def set_tags(self, tags: list[Tag], checked_ids: frozenset[int]) -> None:
        self._tags = tags
        self._checked_ids = checked_ids
        self._apply_filter()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.list_view.viewport():
            # QAbstractItemView drives its own row-hover repainting (the
            # rename/delete icons above) off HoverMove, not MouseMove --
            # mouse-tracking being on doesn't guarantee plain QMouseMove
            # events reach here too, so both are handled the same way.
            if isinstance(event, QMouseEvent | QHoverEvent) and event.type() in (
                QEvent.Type.MouseMove,
                QEvent.Type.HoverMove,
            ):
                index = self.list_view.indexAt(event.position().toPoint())
                self.hover_row_changed.emit(index.row() if index.isValid() else None)
            elif event.type() in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
                self.hover_row_changed.emit(None)
        return super().eventFilter(watched, event)

    def focus_search(self) -> None:
        self.search_box.setFocus()
        self.search_box.selectAll()

    def _unchecked_matches(self, query: str) -> list[Tag]:
        query = query.strip().lower()
        unchecked = [t for t in self._tags if t.id not in self._checked_ids]
        if not query:
            return unchecked
        return [t for t in unchecked if query in t.name.lower()]

    def _apply_filter(self) -> None:
        checked = [t for t in self._tags if t.id in self._checked_ids]
        unchecked = self._unchecked_matches(self.search_box.text())
        self.model.set_tags(checked + unchecked, self._checked_ids)

    def _commit_search(self) -> None:
        query = self.search_box.text().strip()
        if not query:
            return
        matches = self._unchecked_matches(query)
        if matches:
            self.toggle_requested.emit(matches[0].id)
        else:
            self.create_and_check_requested.emit(query)
        self.search_box.clear()
