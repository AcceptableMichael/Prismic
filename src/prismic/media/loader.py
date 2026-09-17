"""Coordinates image decode + downsampling + caching with generation-based
staleness suppression.

Same mechanism family as Phase 2's scan staleness (overview section 7): a
load request that's no longer the most recent one by the time it completes
is discarded rather than allowed to clobber whatever the UI is currently
showing. Thread-safe — the actual background dispatch is the caller's job
(Phase 3's `WorkerPool`); this class only owns request-id bookkeeping and
the cache.

Only the downsampled, display-bound image is cached, not the full original
decode — large images are therefore never retained at full resolution once
loaded here at all, which is the simplest way to satisfy "large images must
not be retained indefinitely at full decoded resolution" (overview section
9). If a future viewer needs the full-resolution data too (e.g. for
pixel-level zoom beyond `max_display_dimension`), that's a re-decode, not a
second cache tier — deliberately not built ahead of an actual Phase 5
requirement for it.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QImage

from prismic.media.cache import ImageCache
from prismic.media.image import ImageLoadError, downsample, load_image

__all__ = ["ImageLoadResult", "ImageLoader", "load_image"]
# `load_image` is re-exported (not just imported for internal use) so tests
# can monkeypatch `prismic.media.loader.load_image` specifically — patching
# `prismic.media.image.load_image` wouldn't affect the name already bound
# here at import time.

_DEFAULT_MAX_DISPLAY_DIMENSION = 2048


@dataclass(frozen=True, slots=True)
class ImageLoadResult:
    request_id: int
    path: Path
    image: QImage | None
    error: str | None


class ImageLoader:
    def __init__(
        self,
        cache: ImageCache | None = None,
        max_display_dimension: int = _DEFAULT_MAX_DISPLAY_DIMENSION,
    ) -> None:
        self._cache = cache if cache is not None else ImageCache()
        self._max_display_dimension = max_display_dimension
        self._lock = threading.Lock()
        self._latest_request_id = 0

    def begin_request(self) -> int:
        with self._lock:
            self._latest_request_id += 1
            return self._latest_request_id

    def is_stale(self, request_id: int) -> bool:
        with self._lock:
            return request_id != self._latest_request_id

    def load(self, request_id: int, path: Path) -> ImageLoadResult | None:
        """Decode (or fetch from cache) `path` for display.

        Returns None if `request_id` is stale — checked both before and
        after the decode itself, since decoding a large image can take
        long enough for a newer request to have superseded this one in the
        meantime. A stale result is discarded rather than returned; it
        must never reach whatever's showing the "current" item.
        """
        if self.is_stale(request_id):
            return None

        cache_key = str(path)
        cached = self._cache.get(cache_key)
        if cached is not None:
            if self.is_stale(request_id):
                return None
            return ImageLoadResult(request_id=request_id, path=path, image=cached, error=None)

        outcome = load_image(path)
        if self.is_stale(request_id):
            return None
        if isinstance(outcome, ImageLoadError):
            return ImageLoadResult(
                request_id=request_id, path=path, image=None, error=outcome.reason
            )

        display_image = downsample(outcome, self._max_display_dimension)
        self._cache.put(cache_key, display_image)
        return ImageLoadResult(request_id=request_id, path=path, image=display_image, error=None)

    def preload(self, request_id: int, path: Path) -> None:
        """Warm the cache for a likely-next item.

        Shares the same generation as regular loads: if the result set has
        since changed (a newer request began), preloading an item from the
        old one is pointless too. There's no "current display slot" here to
        protect beyond that — the bounded cache's own eviction is what
        keeps preloading from growing memory unboundedly, not a stricter
        staleness check.
        """
        if self.is_stale(request_id):
            return
        cache_key = str(path)
        if self._cache.get(cache_key) is not None:
            return
        outcome = load_image(path)
        if isinstance(outcome, ImageLoadError):
            return
        display_image = downsample(outcome, self._max_display_dimension)
        self._cache.put(cache_key, display_image)
