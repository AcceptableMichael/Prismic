"""Candidate media format definition.

This is a placeholder pending Phase 4, which owns real decode-validated
format support (loader.py, image.py, video.py) and the fixture-backed tests
required by overview section 8. Extension membership here is only a
candidate filter for the Phase 2 scanner — "file extensions are only
candidate classification; actual decoding determines validity."
"""

from __future__ import annotations

from pathlib import Path

SUPPORTED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"})

# WebM is the only video format required at minimum per overview section 2.
SUPPORTED_VIDEO_EXTENSIONS = frozenset({".webm"})

SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS


def is_supported_extension(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS
