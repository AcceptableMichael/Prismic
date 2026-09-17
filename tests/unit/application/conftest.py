import sqlite3

import pytest

from prismic.persistence.repositories.mapping_repository import MappingRepository
from prismic.persistence.repositories.media_repository import MediaRepository
from prismic.persistence.repositories.tag_repository import TagRepository


@pytest.fixture
def tags(migrated_connection: sqlite3.Connection) -> TagRepository:
    return TagRepository(migrated_connection)


@pytest.fixture
def media(migrated_connection: sqlite3.Connection) -> MediaRepository:
    return MediaRepository(migrated_connection)


@pytest.fixture
def mappings(migrated_connection: sqlite3.Connection) -> MappingRepository:
    return MappingRepository(migrated_connection)
