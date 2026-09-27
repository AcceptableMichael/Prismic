"""Promotes tags worth checking next to the top of a tag list's
*unchecked* portion, without disturbing where already-checked tags sit.

Two promotion signals, applied as tiers from the top down:

1. "Mega popular" -- tags present on a large enough fraction of the
   collection to be almost always relevant, regardless of context.
2. "Correlated" -- tags that usually co-occur with a tag already checked
   on this item/selection, ranked by how strong that correlation is
   (the strongest match wins when a tag correlates with more than one
   checked tag).

Anything not promoted falls back to whatever relative order the caller
already had (recency, then popularity -- see `TagRecencyTracker`,
`TagRepository.list_all()`). Pure and Qt-free, like the rest of the
application layer: everything it needs is already computed by
`TagCorrelationRepository`/`TagRepository` and handed in.
"""

from __future__ import annotations

from prismic.domain.tag import Tag


def promote_ranked_tags(
    tags: list[Tag],
    checked_ids: frozenset[int],
    *,
    mega_popular_ids: frozenset[int],
    correlations: dict[int, float],
    correlation_threshold: float,
) -> list[Tag]:
    """`tags` with its unchecked entries reordered into promotion tiers.

    Checked tags (`checked_ids`) keep the exact slots they already occupy
    in `tags` -- this only changes the relative order *among* the
    unchecked ones, since the product ask is specifically about ranking
    what to check next, not about where already-checked tags sit.
    """
    unchecked = [tag for tag in tags if tag.id not in checked_ids]

    mega = [tag for tag in unchecked if tag.id in mega_popular_ids]
    remaining = [tag for tag in unchecked if tag.id not in mega_popular_ids]

    correlated = sorted(
        (tag for tag in remaining if correlations.get(tag.id, 0.0) >= correlation_threshold),
        key=lambda tag: correlations[tag.id],
        reverse=True,
    )
    correlated_ids = {tag.id for tag in correlated}
    rest = [tag for tag in remaining if tag.id not in correlated_ids]

    promoted_unchecked = iter(mega + correlated + rest)
    return [tag if tag.id in checked_ids else next(promoted_unchecked) for tag in tags]
