"""Bundled static assets (currently just the app icon).

Paths here are resolved relative to this module rather than via
`importlib.resources`, so they work identically running from source and
running frozen under PyInstaller -- see packaging/prismic.spec's `datas`
entry, which copies icon/ to the same relative location next to the
bundled package.
"""

from __future__ import annotations

from pathlib import Path

ICON_PATH = Path(__file__).resolve().parent / "icon" / "prismic.ico"
