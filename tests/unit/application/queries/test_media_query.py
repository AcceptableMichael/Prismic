import pytest

from prismic.application.queries.media_query import eligible_media
from prismic.domain.media import MediaState
from prismic.persistence.repositories.mapping_repository import MappingRepository
from prismic.persistence.repositories.media_repository import MediaRepository
from prismic.persistence.repositories.tag_repository import TagRepository


def _add_media(
    media: MediaRepository, relative_path: str, state: MediaState = MediaState.ACTIVE
) -> int:
    return media.create(
        relative_path=relative_path, content_hash=relative_path, size=1, mtime=1.0, state=state
    ).id


def test_zero_tags_returns_all_active_media_in_path_order(
    media: MediaRepository, mappings: MappingRepository
) -> None:
    _add_media(media, "z.jpg")
    _add_media(media, "a.jpg")
    _add_media(media, "missing.jpg", state=MediaState.MISSING)

    result = eligible_media(media, mappings, [])

    assert [m.relative_path for m in result] == ["a.jpg", "z.jpg"]


def test_one_tag_returns_only_media_mapped_to_it(
    media: MediaRepository, mappings: MappingRepository, tags: TagRepository
) -> None:
    beach = _add_media(media, "beach.jpg")
    _add_media(media, "unrelated.jpg")
    vacation = tags.create("vacation")
    mappings.add(beach, vacation.id)

    result = eligible_media(media, mappings, [vacation.id])

    assert [m.relative_path for m in result] == ["beach.jpg"]


def test_multiple_tags_is_an_intersection(
    media: MediaRepository, mappings: MappingRepository, tags: TagRepository
) -> None:
    beach = _add_media(media, "beach.jpg")
    mountain = _add_media(media, "mountain.jpg")
    vacation = tags.create("vacation")
    summer = tags.create("summer")
    mappings.add(beach, vacation.id)
    mappings.add(beach, summer.id)
    mappings.add(mountain, vacation.id)

    result = eligible_media(media, mappings, [vacation.id, summer.id])

    assert [m.relative_path for m in result] == ["beach.jpg"]


def test_empty_intersection_is_an_empty_result_not_an_error(
    media: MediaRepository, mappings: MappingRepository, tags: TagRepository
) -> None:
    beach = _add_media(media, "beach.jpg")
    mountain = _add_media(media, "mountain.jpg")
    vacation = tags.create("vacation")
    work = tags.create("work")
    mappings.add(beach, vacation.id)
    mappings.add(mountain, work.id)

    result = eligible_media(media, mappings, [vacation.id, work.id])

    assert result == []


def test_missing_media_is_never_eligible_even_when_tagged(
    media: MediaRepository, mappings: MappingRepository, tags: TagRepository
) -> None:
    gone = _add_media(media, "gone.jpg", state=MediaState.MISSING)
    vacation = tags.create("vacation")
    mappings.add(gone, vacation.id)

    assert eligible_media(media, mappings, [vacation.id]) == []
    assert eligible_media(media, mappings, []) == []


def test_ordering_is_deterministic_by_normalized_relative_path(
    media: MediaRepository, mappings: MappingRepository
) -> None:
    _add_media(media, "b/2.jpg")
    _add_media(media, "a/1.jpg")
    _add_media(media, "b/1.jpg")

    result = eligible_media(media, mappings, [])

    assert [m.relative_path for m in result] == ["a/1.jpg", "b/1.jpg", "b/2.jpg"]


@pytest.mark.slow
def test_scales_acceptably_on_a_large_result_set(
    media: MediaRepository, mappings: MappingRepository
) -> None:
    """A rough smoke-test benchmark, not a rigorous perf target — flags a
    gross regression (e.g. an accidental N+1 query) long before it'd need a
    real number backed by production-scale data."""
    import time

    for index in range(5000):
        _add_media(media, f"photo_{index:05d}.jpg")

    start = time.perf_counter()
    result = eligible_media(media, mappings, [])
    elapsed = time.perf_counter() - start

    assert len(result) == 5000
    assert result[0].relative_path == "photo_00000.jpg"
    assert result[-1].relative_path == "photo_04999.jpg"
    assert elapsed < 2.0
