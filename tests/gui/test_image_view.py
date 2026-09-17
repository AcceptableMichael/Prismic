from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QWheelEvent
from pytestqt.qtbot import QtBot

from prismic.media.image import ImageLoadError, load_image
from prismic.ui.image_view import ImageView

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "media"


def test_set_image_fits_to_window_at_zoom_one(qtbot: QtBot) -> None:
    view = ImageView()
    qtbot.addWidget(view)
    image = load_image(FIXTURES_DIR / "supported_image.png")
    assert not isinstance(image, ImageLoadError)

    view.set_image(image)

    assert view.zoom == 1.0


def test_zoom_in_increases_zoom_level(qtbot: QtBot) -> None:
    view = ImageView()
    qtbot.addWidget(view)
    image = load_image(FIXTURES_DIR / "supported_image.png")
    assert not isinstance(image, ImageLoadError)
    view.set_image(image)

    view.zoom_in()

    assert view.zoom > 1.0


def test_zoom_out_decreases_zoom_level(qtbot: QtBot) -> None:
    view = ImageView()
    qtbot.addWidget(view)
    image = load_image(FIXTURES_DIR / "supported_image.png")
    assert not isinstance(image, ImageLoadError)
    view.set_image(image)

    view.zoom_out()

    assert view.zoom < 1.0


def test_wheel_event_zooms(qtbot: QtBot) -> None:
    view = ImageView()
    qtbot.addWidget(view)
    image = load_image(FIXTURES_DIR / "supported_image.png")
    assert not isinstance(image, ImageLoadError)
    view.set_image(image)
    before = view.zoom

    event = QWheelEvent(
        QPoint(10, 10).toPointF(),
        QPoint(10, 10).toPointF(),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    view.wheelEvent(event)

    assert view.zoom > before


def test_double_click_zooms_in_then_fits_back(qtbot: QtBot) -> None:
    view = ImageView()
    qtbot.addWidget(view)
    view.resize(200, 200)
    image = load_image(FIXTURES_DIR / "supported_image.png")
    assert not isinstance(image, ImageLoadError)
    view.set_image(image)
    assert view.zoom == 1.0

    qtbot.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton)
    assert view.zoom != 1.0

    qtbot.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton)
    assert view.zoom == 1.0


def test_pan_mode_is_scroll_hand_drag(qtbot: QtBot) -> None:
    view = ImageView()
    qtbot.addWidget(view)

    assert view.dragMode() == view.DragMode.ScrollHandDrag
