import pytest

from prismic.application.commands.base import CommandContext
from prismic.application.state import ApplicationState
from prismic.persistence.repositories.mapping_repository import MappingRepository
from prismic.persistence.repositories.media_repository import MediaRepository
from prismic.persistence.repositories.tag_repository import TagRepository


@pytest.fixture
def context(
    tags: TagRepository, media: MediaRepository, mappings: MappingRepository
) -> CommandContext:
    return CommandContext(tags=tags, media=media, mappings=mappings, state=ApplicationState())
