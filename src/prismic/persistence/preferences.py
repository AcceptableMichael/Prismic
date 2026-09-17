"""Location of global application preferences.

Unlike a collection's `.prismic` file, preferences are app-wide, not
per-collection, and live in the platform's standard per-user config
directory rather than inside any collection root.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_APP_NAME = "Prismic"


def preferences_directory() -> Path:
    """The platform config directory Prismic stores app-wide preferences in.

    - Windows: ``%APPDATA%/Prismic``
    - macOS: ``~/Library/Application Support/Prismic``
    - Linux/other: ``$XDG_CONFIG_HOME/prismic`` or ``~/.config/prismic``
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
        return root / _APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / _APP_NAME
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    root = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    return root / _APP_NAME.lower()


def preferences_file_path() -> Path:
    return preferences_directory() / "preferences.json"
