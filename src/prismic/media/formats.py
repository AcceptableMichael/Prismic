"""Candidate media format definition.

Extension membership here is only a candidate filter for the Phase 2
scanner — "file extensions are only candidate classification; actual
decoding determines validity" (overview section 8). Actual decode validity
is `media/image.py` and `media/video.py`'s job.

Both sets below were chosen from, and are validated against, this
project's actual Qt build rather than assumed:

- Image extensions were checked against `QImageReader.supportedImageFormats()`
  (see `tests/unit/media/test_formats.py`) and then curated down to
  conventional photo/collection formats — Qt also reports plugins for
  icons, cursors, PDF, and vector/XPM formats that make no sense for a
  media-collection viewer, so "supported by Qt" alone wasn't the bar.
- WebM support (VP9 video, Opus audio) was validated by actually playing
  the fixtures in `tests/fixtures/media/` through `QMediaPlayer`, not by
  querying `QMediaFormat`'s static capability enum, which reports WebM/VP9/
  Opus as *unsupported* on this build even though real playback works fine.
  See `bootstrap.py` for why the "ffmpeg" Qt Multimedia backend is forced
  explicitly rather than relying on whatever a given install defaults to.
"""

from __future__ import annotations

from pathlib import Path

SUPPORTED_IMAGE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
)

# WebM is the only video format required at minimum per overview section 2.
SUPPORTED_VIDEO_EXTENSIONS = frozenset({".webm"})

SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS


def is_supported_extension(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS
