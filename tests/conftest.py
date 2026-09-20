import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from prismic.persistence import database, migrations


@pytest.fixture(autouse=True)
def isolated_preferences(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point app-wide preferences at a temp directory for every test.

    Preferences (shortcut bindings, so far) live in the real per-user
    config directory by default. Without this, the suite would read
    whatever shortcuts the developer running it has customized -- making
    tests pass or fail depending on whose machine they're on -- and,
    worse, overwrite those customizations the first time a test changed a
    binding.

    Redirected by setting the environment variables
    `preferences_directory()` actually reads, rather than by patching that
    function out, so tests keep exercising the real resolution logic --
    including `test_preferences.py`, which asserts things about it
    directly.
    """
    base = tmp_path / "config"
    base.mkdir()
    monkeypatch.setenv("APPDATA", str(base))  # Windows
    monkeypatch.setenv("XDG_CONFIG_HOME", str(base))  # Linux/other
    monkeypatch.setenv("HOME", str(base))  # macOS, via Path.home()
    return base


@pytest.fixture
def migrated_connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = database.connect(tmp_path / "test.prismic")
    migrations.migrate(connection, tmp_path / "test.prismic")
    try:
        yield connection
    finally:
        connection.close()
