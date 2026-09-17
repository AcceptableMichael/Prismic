import pytest

from prismic.application.commands.base import CommandContext
from prismic.application.commands.filter_commands import (
    FilterDeselectCommand,
    FilterSelectCommand,
)
from prismic.application.errors import TagAlreadySelectedError, TagNotSelectedError
from prismic.persistence.errors import UnknownTagError


def test_select_execute_adds_to_the_filter(context: CommandContext) -> None:
    tag = context.tags.create("vacation")
    command = FilterSelectCommand(tag_id=tag.id)

    command.execute(context)

    assert context.state.selected_tag_ids == [tag.id]


def test_select_undo_removes_from_the_filter(context: CommandContext) -> None:
    tag = context.tags.create("vacation")
    command = FilterSelectCommand(tag_id=tag.id)
    command.execute(context)

    command.undo(context)

    assert context.state.selected_tag_ids == []


def test_select_unknown_tag_raises(context: CommandContext) -> None:
    command = FilterSelectCommand(tag_id=999)

    with pytest.raises(UnknownTagError):
        command.execute(context)


def test_select_an_already_selected_tag_raises(context: CommandContext) -> None:
    tag = context.tags.create("vacation")
    FilterSelectCommand(tag_id=tag.id).execute(context)

    with pytest.raises(TagAlreadySelectedError):
        FilterSelectCommand(tag_id=tag.id).execute(context)


def test_deselect_execute_removes_from_the_filter(context: CommandContext) -> None:
    tag = context.tags.create("vacation")
    FilterSelectCommand(tag_id=tag.id).execute(context)
    command = FilterDeselectCommand(tag_id=tag.id)

    command.execute(context)

    assert context.state.selected_tag_ids == []


def test_deselect_undo_restores_the_filter(context: CommandContext) -> None:
    tag = context.tags.create("vacation")
    FilterSelectCommand(tag_id=tag.id).execute(context)
    command = FilterDeselectCommand(tag_id=tag.id)
    command.execute(context)

    command.undo(context)

    assert context.state.selected_tag_ids == [tag.id]


def test_deselect_a_tag_not_selected_raises(context: CommandContext) -> None:
    tag = context.tags.create("vacation")
    command = FilterDeselectCommand(tag_id=tag.id)

    with pytest.raises(TagNotSelectedError):
        command.execute(context)
