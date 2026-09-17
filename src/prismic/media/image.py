"""Image decoding and downsampling.

Pure functions with no threading/caching concerns of their own (that's
`media/loader.py`'s job) — safe to call from a background thread, so long
as a `QGuiApplication` already exists somewhere in the process (Qt's image
format plugins load through it; this is normally already true by the time
any of this runs, since the app itself needs one to show a window at all).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage


@dataclass(frozen=True, slots=True)
class ImageLoadError:
    """A handled decode failure — corrupt/invalid content, not a crash."""

    path: Path
    reason: str


def load_image(path: Path) -> QImage | ImageLoadError:
    """Decode `path` as an image.

    `QImage` doesn't raise on invalid content; it returns a null image
    instead, which is what actually surfaces a corrupt file (a fixture
    with a `.jpg` extension but garbage bytes decodes to a null `QImage`
    rather than raising) — checked here and turned into a handled result.
    """
    image = QImage(str(path))
    if image.isNull():
        return ImageLoadError(path=path, reason=f"could not decode image data in {path.name}")
    return image


def downsample(image: QImage, max_dimension: int) -> QImage:
    """Scale `image` down to fit within `max_dimension` on its longer side.

    A no-op (returns `image` unchanged) if it already fits — this never
    upscales. Downsampling matters because large images must not be
    retained at full decoded resolution indefinitely (overview section 9);
    the caller (`media/loader.py`) caches the downsampled result, not the
    original decode.
    """
    if image.width() <= max_dimension and image.height() <= max_dimension:
        return image
    return image.scaled(
        max_dimension,
        max_dimension,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
