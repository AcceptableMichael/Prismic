from pathlib import Path

from PySide6.QtGui import QImageReader

from prismic.media.formats import (
    SUPPORTED_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
    is_supported_extension,
)


def test_every_supported_image_extension_is_backed_by_a_real_qt_plugin() -> None:
    """Validated against Qt's actual installed plugins, not assumed."""
    qt_formats = {bytes(f.data()).decode().lower() for f in QImageReader.supportedImageFormats()}
    for extension in SUPPORTED_IMAGE_EXTENSIONS:
        format_name = extension.lstrip(".")
        assert format_name in qt_formats, f"{extension} has no Qt image plugin in this build"


def test_webm_is_the_only_supported_video_extension() -> None:
    assert SUPPORTED_VIDEO_EXTENSIONS == {".webm"}


def test_supported_extensions_is_the_union_of_image_and_video() -> None:
    assert SUPPORTED_EXTENSIONS == SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS


def test_is_supported_extension_is_case_insensitive() -> None:
    assert is_supported_extension(Path("photo.JPG")) is True
    assert is_supported_extension(Path("photo.jpg")) is True
    assert is_supported_extension(Path("notes.txt")) is False
