"""Media eligibility queries: the intersection-filtering semantics from
overview section 4.
"""

from __future__ import annotations

from collections.abc import Sequence

from prismic.domain.media import Media, MediaState
from prismic.persistence.repositories.mapping_repository import MappingRepository
from prismic.persistence.repositories.media_repository import MediaRepository


def eligible_media(
    media_repository: MediaRepository,
    mapping_repository: MappingRepository,
    selected_tag_ids: Sequence[int],
) -> list[Media]:
    """Media eligible under the given filter, ordered by relative path.

    With no selected tags, all discovered media is eligible. With one or
    more, eligibility is the intersection of every selected tag's mappings
    (an empty intersection is a valid, empty result — not an error). Media
    currently missing on disk is never eligible: there's nothing to
    display, filtered or not.
    """
    if selected_tag_ids:
        eligible_ids = set(mapping_repository.media_ids_for_tags(list(selected_tag_ids)))
        candidates = [
            media
            for media in media_repository.list_all()
            if media.id in eligible_ids and media.state == MediaState.ACTIVE
        ]
    else:
        candidates = [
            media for media in media_repository.list_all() if media.state == MediaState.ACTIVE
        ]
    candidates.sort(key=lambda media: media.relative_path)
    return candidates
