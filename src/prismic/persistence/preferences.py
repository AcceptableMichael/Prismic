"""Location of global application preferences.

Unlike a collection's `.prismic` file, preferences are app-wide, not
per-collection, and live in the platform's standard per-user config
directory rather than inside any collection root.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

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


class PreferencesStore:
    """A tiny JSON-backed key/value store for app-wide preferences.

    Deliberately forgiving on read: preferences live in a plain, hand-
    editable file outside any collection, so a missing, unreadable, or
    malformed file is treated as "no preferences yet" rather than an error
    that blocks the app from starting. Nothing in here is authoritative
    data -- the collection database is (see the overview's section 2) --
    so losing a preference to a corrupt file costs the user a setting, and
    refusing to launch over one would cost them the app.

    Writes go via a temporary file in the same directory and an atomic
    replace, so an interrupted save can't leave a half-written file behind
    to be silently discarded by the next read.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else preferences_file_path()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> dict[str, Any]:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except OSError:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(self._path.name + ".tmp")
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self._path)
