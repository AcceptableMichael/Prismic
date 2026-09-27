from pathlib import Path

from pytestqt.qtbot import QtBot

from prismic.application.worker_pool import WorkerPool
from prismic.ui.selection_grid_view import SelectionGridView, _best_grid
from prismic.ui.thumbnail_provider import ThumbnailProvider


def test_a_single_cell_fills_the_whole_available_area() -> None:
    cols, cell_w, cell_h = _best_grid(1, 220, 120)

    assert cols == 1
    assert cell_w == 220 - 2 * 12  # width minus the two side margins
    assert cell_h == 120 - 2 * 12


def test_four_cells_in_a_square_area_form_a_two_by_two_grid() -> None:
    cols, cell_w, cell_h = _best_grid(4, 400, 400)

    assert cols == 2  # 2 cols x 2 rows -- the largest-cell arrangement for a square area
    assert cell_w > 0
    assert cell_h > 0


def test_a_wide_area_prefers_more_columns_than_a_tall_one_for_the_same_count() -> None:
    wide_cols, _wide_w, _wide_h = _best_grid(6, 1200, 300)
    tall_cols, _tall_w, _tall_h = _best_grid(6, 300, 1200)

    assert wide_cols > tall_cols


def test_every_arrangement_actually_fits_every_cell_on_screen() -> None:
    """The chosen (cols, cell size) must never let `rows * cell_h` or
    `cols * cell_w` exceed the available area -- the whole point of the
    search is picking an arrangement that fits, not just a large cell."""
    for count in range(1, 13):
        cols, cell_w, cell_h = _best_grid(count, 500, 350)
        rows = -(-count // cols)  # ceil division
        assert cols * cell_w <= 500 + 1  # +1 for float slop
        assert rows * cell_h <= 350 + 1


def test_grid_view_renders_without_crashing_and_requests_missing_thumbnails(
    qtbot: QtBot, tmp_path: Path
) -> None:
    (tmp_path / "a.jpg").write_bytes(b"not a real image, just needs to exist")
    (tmp_path / "b.jpg").write_bytes(b"not a real image, just needs to exist")

    provider = ThumbnailProvider()
    pool = WorkerPool()
    view = SelectionGridView(provider, lambda: pool)
    qtbot.addWidget(view)
    view.resize(400, 300)

    view.set_items([(1, tmp_path / "a.jpg"), (2, tmp_path / "b.jpg")])
    view.show()
    qtbot.waitExposed(view)

    # Neither is cached yet, so painting should have kicked off a decode
    # request for each rather than raising.
    qtbot.waitUntil(lambda: provider.has_failed(1) or provider.get(1) is not None, timeout=5000)

    pool.shutdown(wait=True)
