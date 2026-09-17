from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QListView
from pytestqt.qtbot import QtBot

from prismic.domain.tag import Tag
from prismic.ui.tag_model import TagListModel
from prismic.ui.tag_row_delegate import TagRowDelegate


def _build(qtbot: QtBot) -> tuple[QListView, TagListModel, TagRowDelegate]:
    view = QListView()
    qtbot.addWidget(view)
    model = TagListModel()
    view.setModel(model)
    delegate = TagRowDelegate(view, view)
    view.setItemDelegate(delegate)
    model.set_tags([Tag(id=1, name="kittens"), Tag(id=2, name="sunset")], frozenset({2}))
    view.resize(220, 200)
    view.show()
    qtbot.waitExposed(view)
    return view, model, delegate


def test_clicking_anywhere_on_a_row_toggles_it_not_just_the_checkbox(qtbot: QtBot) -> None:
    view, model, delegate = _build(qtbot)
    toggled: list[int] = []
    delegate.toggle_requested.connect(toggled.append)
    index = model.index(0, 0)  # "kittens", unchecked
    row_rect = view.visualRect(index)
    # Click near the far-right edge of the row -- nowhere near the
    # checkbox -- to prove the whole row is the toggle target, not just
    # the small indicator box.
    far_right = row_rect.center()
    far_right.setX(row_rect.right() - 2)

    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=far_right)

    # Emission is deferred a tick past the click (see `_emit_later`'s
    # docstring in tag_row_delegate.py) so the handler's model reset can't
    # land while the view is still mid-dispatch of this same mouse event.
    qtbot.waitUntil(lambda: toggled == [1], timeout=1000)


def test_clicking_the_delete_icon_emits_delete_not_toggle(qtbot: QtBot) -> None:
    view, model, delegate = _build(qtbot)
    toggled: list[int] = []
    deleted: list[int] = []
    delegate.toggle_requested.connect(toggled.append)
    delegate.delete_requested.connect(deleted.append)
    index = model.index(0, 0)
    row_rect = view.visualRect(index)
    _checkbox, _rename, delete_rect = delegate._rects(row_rect)  # noqa: SLF001 - white-box test

    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=delete_rect.center())
    qtbot.waitUntil(lambda: deleted == [1], timeout=1000)

    assert toggled == []


def test_clicking_the_rename_icon_starts_inline_editing_not_toggle(qtbot: QtBot) -> None:
    view, model, delegate = _build(qtbot)
    toggled: list[int] = []
    delegate.toggle_requested.connect(toggled.append)
    index = model.index(0, 0)
    row_rect = view.visualRect(index)
    _checkbox, rename_rect, _delete = delegate._rects(row_rect)  # noqa: SLF001 - white-box test

    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=rename_rect.center())

    assert view.indexWidget(index) is not None
    qtbot.wait(50)  # give a wrongly-fired deferred toggle a chance to arrive before checking
    assert toggled == []


def test_committing_a_rename_emits_rename_committed_not_a_model_write(qtbot: QtBot) -> None:
    view, model, delegate = _build(qtbot)
    renamed: list[tuple[int, str]] = []
    delegate.rename_committed.connect(lambda tag_id, name: renamed.append((tag_id, name)))
    index = model.index(0, 0)
    view.edit(index)
    editor = view.indexWidget(index)
    assert isinstance(editor, QLineEdit)

    editor.setText("felines")
    qtbot.keyClick(editor, Qt.Key.Key_Return)

    assert renamed == [(1, "felines")]
    # The model itself never changes -- TagListModel is display-only; a
    # real rename only happens once the caller dispatches a command and
    # calls set_tags() again.
    assert model.tag_at(0).name == "kittens"
