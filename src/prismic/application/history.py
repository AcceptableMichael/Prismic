"""Session-local undo history.

Cleared on restart (in-memory only, never persisted) per overview section 5.
Redo is explicitly out of scope for v1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prismic.application.commands.base import Command


class History:
    def __init__(self) -> None:
        self._stack: list[Command] = []

    def push(self, command: Command) -> None:
        self._stack.append(command)

    def pop(self) -> Command | None:
        """Pop and return the most recent command, or None if empty."""
        if not self._stack:
            return None
        return self._stack.pop()

    def can_undo(self) -> bool:
        return bool(self._stack)

    def __len__(self) -> int:
        return len(self._stack)
