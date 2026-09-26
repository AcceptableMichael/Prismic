"""Rasterizes assets/icon/prismic-icon.svg into the .ico and .png files the
app and installer need. Re-run this whenever the source SVG changes:

    uv run python tools/generate_icon.py

Windows .ico files can hold PNG-compressed frames (supported since Vista),
which is what this writes -- there's no need for a raw-DIB encoder.

Small sizes are NOT rendered by asking QSvgRenderer to draw directly at
16x16/32x32/etc -- that renders with antialiasing effectively defeated
(the fine 7-unit-wide outline strokes collapse to sub-pixel widths and come
out jagged/blocky) and produced visibly bad icons. Instead this renders once
at a large base resolution with antialiasing on, then mipmap-downsamples
(repeated 2x box-ish reduction via smooth scaling, not one big jump) to each
target size -- the standard technique for minifying detailed source art
without aliasing.
"""

from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_SVG = REPO_ROOT / "assets" / "icon" / "prismic-icon.svg"
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
PNG_SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]
ICO_OUT = REPO_ROOT / "src" / "prismic" / "assets" / "icon" / "prismic.ico"
PNG_DIR = REPO_ROOT / "assets" / "icon" / "png"

BASE_RESOLUTION = 2048  # rendered once, antialiased, then downsampled from


def render_base_image(renderer: QSvgRenderer) -> QImage:
    image = QImage(QSize(BASE_RESOLUTION, BASE_RESOLUTION), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0x00000000)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()
    return image


def mipmap_downsample(image: QImage, target: int) -> QImage:
    current = image
    # Halve repeatedly until the next halving would undershoot the target --
    # each 2x step is a well-conditioned reduction for smooth scaling, unlike
    # jumping straight from 2048 to e.g. 16 in one bilinear pass.
    while current.width() // 2 >= target:
        next_size = current.width() // 2
        current = current.scaled(
            next_size,
            next_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    if current.width() != target:
        current = current.scaled(
            target,
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return current


def image_to_png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    data = bytes(buffer.data().data())
    buffer.close()
    return data


def write_ico(png_by_size: dict[int, bytes], out_path: Path) -> None:
    sizes = sorted(png_by_size)
    count = len(sizes)
    header = struct.pack("<HHH", 0, 1, count)  # reserved, type=icon, count

    dir_entries = b""
    image_data = b""
    offset = 6 + count * 16  # header + one 16-byte entry per image
    for size in sizes:
        png_bytes = png_by_size[size]
        wh = size if size < 256 else 0  # 0 means 256 in the ICO format
        entry = struct.pack(
            "<BBBBHHII",
            wh,  # width
            wh,  # height
            0,  # color count (0 = no palette, true color)
            0,  # reserved
            1,  # color planes
            32,  # bits per pixel
            len(png_bytes),
            offset,
        )
        dir_entries += entry
        image_data += png_bytes
        offset += len(png_bytes)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(header + dir_entries + image_data)


def main() -> None:
    app = QApplication.instance() or QApplication([])
    renderer = QSvgRenderer(str(SOURCE_SVG))
    if not renderer.isValid():
        raise SystemExit(f"Failed to load {SOURCE_SVG}")

    base_image = render_base_image(renderer)

    png_by_size = {
        size: image_to_png_bytes(mipmap_downsample(base_image, size))
        for size in set(ICO_SIZES) | set(PNG_SIZES)
    }

    write_ico({size: png_by_size[size] for size in ICO_SIZES}, ICO_OUT)
    print(f"Wrote {ICO_OUT}")

    PNG_DIR.mkdir(parents=True, exist_ok=True)
    for size in PNG_SIZES:
        out = PNG_DIR / f"prismic-{size}.png"
        out.write_bytes(png_by_size[size])
        print(f"Wrote {out}")

    del app


if __name__ == "__main__":
    main()
