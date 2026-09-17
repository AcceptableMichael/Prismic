"""Generates the binary test fixtures under `tests/fixtures/media/`.

Run with:

    uv run python tools/generate_media_fixtures.py

Requires the `imageio-ffmpeg` dev dependency (a bundled static ffmpeg
binary, used only to author the WebM fixtures) — the generated files
themselves are committed to the repo, so this script only needs rerunning
if a fixture actually needs to change, not as part of every test run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "media"


def _write_supported_image() -> None:
    image = QImage(64, 64, QImage.Format.Format_RGB32)
    image.fill(QColor("steelblue"))
    painter = QPainter(image)
    painter.setPen(QColor("white"))
    painter.drawLine(0, 0, 63, 63)
    painter.end()
    path = FIXTURES_DIR / "supported_image.png"
    if not image.save(str(path)):
        raise RuntimeError(f"failed to write {path}")


def _write_large_image() -> None:
    width, height = 3000, 2000
    image = QImage(width, height, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, QColor("darkred"))
    gradient.setColorAt(0.5, QColor("gold"))
    gradient.setColorAt(1.0, QColor("navy"))
    painter.fillRect(image.rect(), gradient)
    # A grid on top of the gradient so the raster isn't trivially flat and
    # compresses more like real photographic content, for downsample/cache
    # testing.
    painter.setPen(QColor("white"))
    for x in range(0, width, 137):
        painter.drawLine(x, 0, x, height)
    for y in range(0, height, 149):
        painter.drawLine(0, y, width, y)
    painter.end()
    path = FIXTURES_DIR / "large_image.png"
    if not image.save(str(path)):
        raise RuntimeError(f"failed to write {path}")


def _write_corrupt_image() -> None:
    path = FIXTURES_DIR / "corrupt_image.jpg"
    path.write_bytes(b"this has a .jpg extension but is not valid image data whatsoever" * 20)


def _write_corrupt_video() -> None:
    path = FIXTURES_DIR / "corrupt_video.webm"
    path.write_bytes(b"this has a .webm extension but is not a valid container" * 20)


def _write_unsupported_file() -> None:
    path = FIXTURES_DIR / "unsupported.txt"
    path.write_text("plain text, not a candidate media extension at all\n", encoding="utf-8")


def _run_ffmpeg(*args: str) -> None:
    import imageio_ffmpeg

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg_exe, "-y", *args], check=True, capture_output=True)


def _write_supported_video() -> None:
    # Explicit yuv420p (VP9 profile 0): the widely-supported baseline chroma
    # format, rather than whatever testsrc's default happens to be (which
    # produced a profile-1 gbrp stream some decoders are pickier about).
    path = FIXTURES_DIR / "supported_video.webm"
    _run_ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x240:rate=15:duration=1",
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "200k",
        str(path),
    )


def _write_audio_video() -> None:
    path = FIXTURES_DIR / "audio_video.webm"
    _run_ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x240:rate=15:duration=1",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=1",
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "200k",
        "-c:a",
        "libopus",
        "-b:a",
        "64k",
        "-shortest",
        str(path),
    )


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    # QImage.save() silently fails without a QGuiApplication instance to
    # load its image-format plugins through.
    app = QGuiApplication(sys.argv[:1])
    _write_supported_image()
    _write_large_image()
    _write_corrupt_image()
    _write_corrupt_video()
    _write_unsupported_file()
    _write_supported_video()
    _write_audio_video()
    del app
    print(f"Wrote fixtures to {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
