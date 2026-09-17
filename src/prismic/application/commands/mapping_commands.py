"""Media/tag mapping creation and deletion commands."""

from __future__ import annotations

from dataclasses import dataclass

from prismic.application.commands.base import Command, CommandContext
from prismic.application.errors import UnknownMappingError
from prismic.persistence.errors import UnknownMediaError, UnknownTagError


@dataclass
class MappingAddCommand(Command):
    media_id: int
    tag_id: int

    def execute(self, context: CommandContext) -> None:
        if context.media.get(self.media_id) is None:
            raise UnknownMediaError(self.media_id)
        if context.tags.get(self.tag_id) is None:
            raise UnknownTagError(self.tag_id)
        context.mappings.add(self.media_id, self.tag_id)

    def undo(self, context: CommandContext) -> None:
        context.mappings.remove(self.media_id, self.tag_id)


@dataclass
class MappingRemoveCommand(Command):
    media_id: int
    tag_id: int

    def execute(self, context: CommandContext) -> None:
        existing_tag_ids = {tag.id for tag in context.mappings.tags_for_media(self.media_id)}
        if self.tag_id not in existing_tag_ids:
            raise UnknownMappingError(self.media_id, self.tag_id)
        context.mappings.remove(self.media_id, self.tag_id)

    def undo(self, context: CommandContext) -> None:
        context.mappings.add(self.media_id, self.tag_id)
