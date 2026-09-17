"""Filter (active tag selection) commands.

Per overview section 7, filter selection/deselection is undoable too, just
like the persistent commands — even though the mutation itself is purely
in-memory session state, not a database write.
"""

from __future__ import annotations

from dataclasses import dataclass

from prismic.application.commands.base import Command, CommandContext
from prismic.application.errors import TagAlreadySelectedError, TagNotSelectedError
from prismic.persistence.errors import UnknownTagError


@dataclass
class FilterSelectCommand(Command):
    tag_id: int

    def execute(self, context: CommandContext) -> None:
        if context.tags.get(self.tag_id) is None:
            raise UnknownTagError(self.tag_id)
        if self.tag_id in context.state.selected_tag_ids:
            raise TagAlreadySelectedError(self.tag_id)
        context.state.selected_tag_ids.append(self.tag_id)

    def undo(self, context: CommandContext) -> None:
        context.state.selected_tag_ids.remove(self.tag_id)


@dataclass
class FilterDeselectCommand(Command):
    tag_id: int

    def execute(self, context: CommandContext) -> None:
        if self.tag_id not in context.state.selected_tag_ids:
            raise TagNotSelectedError(self.tag_id)
        context.state.selected_tag_ids.remove(self.tag_id)

    def undo(self, context: CommandContext) -> None:
        context.state.selected_tag_ids.append(self.tag_id)
