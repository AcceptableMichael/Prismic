"""A bounded, LRU-evicted cache for decoded image data.

Keeps total memory use under a byte budget rather than a fixed item count,
since decoded image size varies enormously — `QImage.sizeInBytes()` gives
the actual in-memory footprint, so a handful of large photos and a hundred
thumbnails are weighed the same way.
"""

from __future__ import annotations

from collections import OrderedDict

from PySide6.QtGui import QImage

_DEFAULT_MAX_BYTES = 256 * 1024 * 1024  # 256 MiB


class ImageCache:
    def __init__(self, max_bytes: int = _DEFAULT_MAX_BYTES) -> None:
        self._max_bytes = max_bytes
        self._entries: OrderedDict[str, QImage] = OrderedDict()
        self._current_bytes = 0

    def get(self, key: str) -> QImage | None:
        image = self._entries.get(key)
        if image is not None:
            self._entries.move_to_end(key)  # most-recently-used
        return image

    def put(self, key: str, image: QImage) -> None:
        existing = self._entries.pop(key, None)
        if existing is not None:
            self._current_bytes -= existing.sizeInBytes()
        self._entries[key] = image
        self._current_bytes += image.sizeInBytes()
        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        while self._current_bytes > self._max_bytes and self._entries:
            _, oldest = self._entries.popitem(last=False)
            self._current_bytes -= oldest.sizeInBytes()

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def current_bytes(self) -> int:
        return self._current_bytes

    @property
    def max_bytes(self) -> int:
        return self._max_bytes
