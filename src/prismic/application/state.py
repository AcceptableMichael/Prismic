"""Session-visible application state: the active filter, result set, and
current item, with the invariant from overview section 4 enforced at every
recompute: `current_item` is always either `null` or a member of the active
result set.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prismic.application.queries.media_query import eligible_media
from prismic.persistence.repositories.mapping_repository import MappingRepository
from prismic.persistence.repositories.media_repository import MediaRepository


@dataclass
class ApplicationState:
    selected_tag_ids: list[int] = field(default_factory=list)
    result_set: list[int] = field(default_factory=list)
    """Media ids currently eligible under the active filter, ordered by
    normalized relative path ascending."""
    current_item: int | None = None

    def recompute(
        self, media_repository: MediaRepository, mapping_repository: MappingRepository
    ) -> None:
        """Recalculate `result_set` from the current filter and repair
        `current_item` if the recalculation invalidated it.

        Called after every command, so the invariant holds continuously
        rather than relying on each command to reason about whether its own
        mutation could have affected eligibility.
        """
        previous_order = self.result_set
        previous_current = self.current_item

        media = eligible_media(media_repository, mapping_repository, self.selected_tag_ids)
        self.result_set = [item.id for item in media]
        self.current_item = self._resolve_current_item(previous_order, previous_current)

    def _resolve_current_item(
        self, previous_order: list[int], previous_current: int | None
    ) -> int | None:
        if previous_current is None:
            return None
        if previous_current in self.result_set:
            return previous_current

        # The current item left the result set: find the nearest surviving
        # item in the previous navigation order; if none survives, the
        # first result; if there are no results, null.
        still_present = set(self.result_set)
        if previous_current in previous_order:
            index = previous_order.index(previous_current)
            nearest = _nearest_surviving(previous_order, index, still_present)
            if nearest is not None:
                return nearest

        return self.result_set[0] if self.result_set else None


def _nearest_surviving(
    previous_order: list[int], index: int, still_present: set[int]
) -> int | None:
    """The id in `previous_order` closest to `index` that's still in
    `still_present`, preferring the following item over the preceding one
    at equal distance."""
    max_distance = max(index, len(previous_order) - 1 - index)
    for distance in range(1, max_distance + 1):
        forward = index + distance
        if forward < len(previous_order) and previous_order[forward] in still_present:
            return previous_order[forward]
        backward = index - distance
        if backward >= 0 and previous_order[backward] in still_present:
            return previous_order[backward]
    return None
