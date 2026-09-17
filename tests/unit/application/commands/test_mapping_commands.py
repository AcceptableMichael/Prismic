import pytest

from prismic.application.commands.base import CommandContext
from prismic.application.commands.mapping_commands import MappingAddCommand, MappingRemoveCommand
from prismic.application.errors import UnknownMappingError
from prismic.domain.media import MediaState
from prismic.persistence.errors import UnknownMediaError, UnknownTagError
from prismic.persistence.repositories.media_repository import MediaRepository


def _make_media(media: MediaRepository) -> int:
    return media.create(
        relative_path="a.jpg", content_hash="a", size=1, mtime=1.0, state=MediaState.ACTIVE
    ).id


def test_add_execute_creates_the_mapping(context: CommandContext, media: MediaRepository) -> None:
    media_id = _make_media(media)
    tag = context.tags.create("vacation")
    command = MappingAddCommand(media_id=media_id, tag_id=tag.id)

    command.execute(context)

    assert [t.id for t in context.mappings.tags_for_media(media_id)] == [tag.id]


def test_add_undo_removes_the_mapping(context: CommandContext, media: MediaRepository) -> None:
    media_id = _make_media(media)
    tag = context.tags.create("vacation")
    command = MappingAddCommand(media_id=media_id, tag_id=tag.id)
    command.execute(context)

    command.undo(context)

    assert context.mappings.tags_for_media(media_id) == []


def test_add_with_unknown_media_raises(context: CommandContext) -> None:
    tag = context.tags.create("vacation")
    command = MappingAddCommand(media_id=999, tag_id=tag.id)

    with pytest.raises(UnknownMediaError):
        command.execute(context)


def test_add_with_unknown_tag_raises(context: CommandContext, media: MediaRepository) -> None:
    media_id = _make_media(media)
    command = MappingAddCommand(media_id=media_id, tag_id=999)

    with pytest.raises(UnknownTagError):
        command.execute(context)


def test_remove_execute_deletes_the_mapping(
    context: CommandContext, media: MediaRepository
) -> None:
    media_id = _make_media(media)
    tag = context.tags.create("vacation")
    context.mappings.add(media_id, tag.id)
    command = MappingRemoveCommand(media_id=media_id, tag_id=tag.id)

    command.execute(context)

    assert context.mappings.tags_for_media(media_id) == []


def test_remove_undo_recreates_the_mapping(context: CommandContext, media: MediaRepository) -> None:
    media_id = _make_media(media)
    tag = context.tags.create("vacation")
    context.mappings.add(media_id, tag.id)
    command = MappingRemoveCommand(media_id=media_id, tag_id=tag.id)
    command.execute(context)

    command.undo(context)

    assert [t.id for t in context.mappings.tags_for_media(media_id)] == [tag.id]


def test_remove_a_mapping_that_does_not_exist_raises(
    context: CommandContext, media: MediaRepository
) -> None:
    media_id = _make_media(media)
    tag = context.tags.create("vacation")
    command = MappingRemoveCommand(media_id=media_id, tag_id=tag.id)

    with pytest.raises(UnknownMappingError):
        command.execute(context)
