import sqlite3

import pytest

from prismic.domain.tag import InvalidTagNameError
from prismic.persistence.errors import DuplicateTagNameError, UnknownTagError
from prismic.persistence.repositories.tag_repository import TagRepository


@pytest.fixture
def repository(migrated_connection: sqlite3.Connection) -> TagRepository:
    return TagRepository(migrated_connection)


def test_create_returns_a_tag_with_a_trimmed_name(repository: TagRepository) -> None:
    tag = repository.create("  vacation  ")

    assert tag.name == "vacation"
    assert tag.id is not None


def test_create_rejects_an_invalid_name(repository: TagRepository) -> None:
    with pytest.raises(InvalidTagNameError):
        repository.create("   ")


def test_create_rejects_an_exact_duplicate_name(repository: TagRepository) -> None:
    repository.create("vacation")

    with pytest.raises(DuplicateTagNameError):
        repository.create("vacation")


def test_names_are_case_sensitive(repository: TagRepository) -> None:
    repository.create("vacation")

    lowercase_variant = repository.create("Vacation")

    assert lowercase_variant.name == "Vacation"


def test_rename_updates_the_stored_name(repository: TagRepository) -> None:
    tag = repository.create("vacation")

    renamed = repository.rename(tag.id, "travel")

    assert renamed.name == "travel"
    assert repository.get(tag.id).name == "travel"  # type: ignore[union-attr]


def test_rename_to_an_existing_name_raises(repository: TagRepository) -> None:
    repository.create("vacation")
    other = repository.create("travel")

    with pytest.raises(DuplicateTagNameError):
        repository.rename(other.id, "vacation")


def test_rename_unknown_tag_raises(repository: TagRepository) -> None:
    with pytest.raises(UnknownTagError):
        repository.rename(999, "anything")


def test_delete_removes_the_tag(repository: TagRepository) -> None:
    tag = repository.create("vacation")

    repository.delete(tag.id)

    assert repository.get(tag.id) is None


def test_delete_unknown_tag_raises(repository: TagRepository) -> None:
    with pytest.raises(UnknownTagError):
        repository.delete(999)


def test_get_returns_none_for_unknown_id(repository: TagRepository) -> None:
    assert repository.get(999) is None


def test_list_all_is_ordered_by_name(repository: TagRepository) -> None:
    repository.create("zebra")
    repository.create("apple")
    repository.create("mango")

    assert [tag.name for tag in repository.list_all()] == ["apple", "mango", "zebra"]
