import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from prismic.persistence import database, migrations


@pytest.fixture
def migrated_connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = database.connect(tmp_path / "test.prismic")
    migrations.migrate(connection, tmp_path / "test.prismic")
    try:
        yield connection
    finally:
        connection.close()
