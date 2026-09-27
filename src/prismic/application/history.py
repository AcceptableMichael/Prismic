"""Session-local undo/redo history.

Cleared on restart (in-memory only, never persisted) per overview section 5.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prismic.application.commands.base import Command


class History:
    def __init__(self) -> None:
        self._undo_stack: list[Command] = []
        # A fresh command (`push`) invalidates whatever was redoable --
        # same convention as every other undo/redo stack -- so redoing
        # never resurrects a branch the user has since diverged from.
        self._redo_stack: list[Command] = []

    def push(self, command: Command) -> None:
        self._undo_stack.append(command)
        self._redo_stack.clear()

    def pop_undo(self) -> Command | None:
        """Move the most recent command onto the redo stack and return
        it, or None if there's nothing to undo."""
        if not self._undo_stack:
            return None
        command = self._undo_stack.pop()
        self._redo_stack.append(command)
        return command

    def pop_redo(self) -> Command | None:
        """Move the most recently undone command back onto the undo
        stack and return it, or None if there's nothing to redo."""
        if not self._redo_stack:
            return None
        command = self._redo_stack.pop()
        self._undo_stack.append(command)
        return command

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def __len__(self) -> int:
        return len(self._undo_stack)
