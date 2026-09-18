"""Rasterizes assets/icon/prismic-icon.svg into the .ico and .png files the
app and installer need. Re-run this whenever the source SVG changes:

    uv run python tools/generate_icon.py

Windows .ico files can hold PNG-compressed frames (supported since Vista),
which is what this writes -- there's no need for a raw-DIB encoder.
"""

from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_SVG = REPO_ROOT / "assets" / "icon" / "prismic-icon.svg"
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
PNG_SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]
ICO_OUT = REPO_ROOT / "src" / "prismic" / "assets" / "icon" / "prismic.ico"
PNG_DIR = REPO_ROOT / "assets" / "icon" / "png"


def render_png(renderer: QSvgRenderer, size: int) -> bytes:
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(0x00000000)  # transparent
    painter_target = pixmap
    from PySide6.QtGui import QPainter

    painter = QPainter(painter_target)
    renderer.render(painter)
    painter.end()

    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    data = bytes(buffer.data())
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

    png_by_size = {size: render_png(renderer, size) for size in set(ICO_SIZES) | set(PNG_SIZES)}

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
