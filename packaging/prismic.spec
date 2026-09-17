# PyInstaller build spec for Prismic. See phases/07-distribution.md for the
# bundler choice and rationale.
#
# Build from the repo root with:
#   uv run --project . pyinstaller packaging/prismic.spec --noconfirm
# (or, from a venv that already has pyinstaller installed:
#   pyinstaller packaging/prismic.spec --noconfirm)
#
# Qt Multimedia's ffmpeg backend plugin isn't picked up by PyInstaller's
# default PySide6 hook (it only collects the plugin *categories* it thinks
# an app needs, and "multimedia" isn't inferred from a plain `QApplication`
# import) -- verified by building without the explicit `datas` entry below
# first and hitting "Failed to find a working backend" / no ffmpeg plugin
# in dist/. Must be included explicitly, per the Phase 4 finding that the
# ffmpeg backend (not the default "windows" one) is required for WebM
# playback -- see bootstrap.py.

from __future__ import annotations

import os

from PySide6 import __file__ as pyside6_init

pyside6_dir = os.path.dirname(pyside6_init)
multimedia_plugin_dir = os.path.join(pyside6_dir, "plugins", "multimedia")

multimedia_plugins = [
    (os.path.join(multimedia_plugin_dir, name), os.path.join("PySide6", "plugins", "multimedia"))
    for name in os.listdir(multimedia_plugin_dir)
]

a = Analysis(
    ["../src/prismic/__main__.py"],
    pathex=["../src"],
    binaries=multimedia_plugins,
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="prismic",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
