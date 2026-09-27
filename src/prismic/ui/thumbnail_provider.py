"""Async, cached thumbnail decoding for the result list.

Same staleness family as `media/loader.py::ImageLoader`, sized down for
this purpose: a generation counter is bumped whenever the provider is
reset (switching collections), and any in-flight decode from a prior
generation is dropped rather than allowed to populate the new collection's
cache under a possibly-reused media id.

Decoding happens on `PrismicSession.worker_pool` -- the same background
pool everything else in the app uses -- and results are marshaled back to
the GUI thread via `FutureWatcher`'s queued-signal mechanism. This class
never touches Qt widgets directly; it only caches `QPixmap`s and signals
that one became available, leaving painting to `ThumbnailDelegate`.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage, QPixmap

from prismic.application.worker_pool import WorkerPool
from prismic.media.image import ImageLoadError, downsample, load_image
from prismic.ui.future_watcher import FutureWatcher

THUMBNAIL_DIMENSION = 160


def _decode_thumbnail(path: Path, dimension: int) -> QImage | None:
    outcome = load_image(path)
    if isinstance(outcome, ImageLoadError):
        return None
    return downsample(outcome, dimension)


class ThumbnailProvider(QObject):
    thumbnail_ready = Signal(int)  # media_id
    decode_failed = Signal(int)  # media_id -- lets the delegate stop retrying

    def __init__(self, dimension: int = THUMBNAIL_DIMENSION, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # Default dimension for a plain `request()` call. `ThumbnailDelegate`
        # relies on this default since the result list's rows are a fixed
        # size. `SelectionGridView`'s cells are not fixed -- they grow with
        # the window and shrink with selection count -- so it passes an
        # explicit `dimension` per request instead; see `request()`.
        self._dimension = dimension
        self._cache: dict[int, QPixmap] = {}
        self._decoded_at: dict[int, int] = {}
        self._pending: set[int] = set()
        self._failed: set[int] = set()
        self._watchers: list[FutureWatcher] = []
        self._generation = 0

    def get(self, media_id: int) -> QPixmap | None:
        return self._cache.get(media_id)

    def has_failed(self, media_id: int) -> bool:
        return media_id in self._failed

    def request(
        self, media_id: int, path: Path, worker_pool: WorkerPool, dimension: int | None = None
    ) -> None:
        """Decode a thumbnail for `media_id`, at `dimension` (defaulting to
        the provider's own) if not already cached at that size or larger.

        A cache hit at a *smaller* dimension than requested still triggers
        a re-decode -- letting a caller whose display size grew (a grid
        cell after a window resize, or a selection shrinking to fewer
        items) ask for a sharper version without needing its own
        cache-invalidation logic. `downsample()` never upscales, so asking
        for a dimension larger than the source image is harmless -- it
        just decodes at the image's own resolution.
        """
        if media_id in self._failed:
            return
        target = self._dimension if dimension is None else dimension
        if media_id in self._pending or self._decoded_at.get(media_id, 0) >= target:
            return
        self._pending.add(media_id)
        generation = self._generation
        future = worker_pool.submit(_decode_thumbnail, path, target)
        watcher = FutureWatcher(future, self)
        watcher.finished.connect(lambda image: self._on_done(media_id, generation, target, image))
        self._watchers.append(watcher)

    def reset(self) -> None:
        self._generation += 1
        self._cache.clear()
        self._decoded_at.clear()
        self._pending.clear()
        self._failed.clear()
        self._watchers.clear()

    def _on_done(
        self, media_id: int, generation: int, dimension: int, image: QImage | None
    ) -> None:
        self._pending.discard(media_id)
        if generation != self._generation:
            return
        if image is None:
            self._failed.add(media_id)
            self.decode_failed.emit(media_id)
            return
        self._cache[media_id] = QPixmap.fromImage(image)
        self._decoded_at[media_id] = dimension
        self.thumbnail_ready.emit(media_id)
