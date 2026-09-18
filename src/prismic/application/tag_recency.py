"""Tracks when each tag was last clicked, so the tag list views can float
recently-used tags to the top.

Purely in-memory and session-scoped: clicking a tag to select/deselect it
isn't a domain mutation in its own right (it has no undo/redo story beyond
whatever command the click triggers), so it doesn't go through the command
dispatcher or get persisted.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from prismic.domain.tag import Tag

_WINDOW_SECONDS = 30 * 60


@dataclass
class TagRecencyTracker:
    _clock: Callable[[], float] = time.monotonic
    _clicked_at: dict[int, float] = field(default_factory=dict)

    def record_click(self, tag_id: int) -> None:
        self._clicked_at[tag_id] = self._clock()

    def order(self, tags: list[Tag]) -> list[Tag]:
        """Tags clicked within the last 30 minutes first (most recent
        click first), then the rest in whatever order they were given --
        the caller's default ordering (see `TagRepository.list_all`)."""
        now = self._clock()
        recent: list[tuple[float, Tag]] = []
        rest: list[Tag] = []
        for tag in tags:
            clicked_at = self._clicked_at.get(tag.id)
            if clicked_at is not None and now - clicked_at <= _WINDOW_SECONDS:
                recent.append((clicked_at, tag))
            else:
                rest.append(tag)
        recent.sort(key=lambda item: item[0], reverse=True)
        return [tag for _, tag in recent] + rest
