"""Session-visible application state: the active filter, result set, and
current item, with the invariant from overview section 4 enforced at every
recompute: `current_item` is always either `null` or a member of the active
result set.

`selected_items` extends that single-item model to a bulk selection (see
`ui/result_list_view.py`'s additive shift/ctrl-click): every id in it is
also a member of the result set, and `current_item` -- the click/keyboard
"anchor," used for both single-item display and as the shift-click range
endpoint -- is always itself a member of `selected_items` whenever
`current_item` isn't null. A plain, unmodified selection (one item) is
`selected_items == {current_item}`; multi-select is anything bigger.
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
    selected_items: frozenset[int] = field(default_factory=frozenset)

    def recompute(
        self, media_repository: MediaRepository, mapping_repository: MappingRepository
    ) -> None:
        """Recalculate `result_set` from the current filter and repair
        `current_item`/`selected_items` if the recalculation invalidated
        either.

        Called after every command, so the invariant holds continuously
        rather than relying on each command to reason about whether its own
        mutation could have affected eligibility.
        """
        previous_order = self.result_set
        previous_current = self.current_item

        media = eligible_media(media_repository, mapping_repository, self.selected_tag_ids)
        self.result_set = [item.id for item in media]
        self.current_item = self._resolve_current_item(previous_order, previous_current)

        still_present = set(self.result_set)
        selected = {item_id for item_id in self.selected_items if item_id in still_present}
        if self.current_item is not None:
            selected.add(self.current_item)
        self.selected_items = frozenset(selected)

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
