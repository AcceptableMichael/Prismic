from pathlib import Path

from prismic.domain.collection import Collection


def test_is_collection_file_matches_its_own_database_path(tmp_path: Path) -> None:
    database_path = tmp_path / "vacation.prismic"
    database_path.touch()
    collection = Collection(root=tmp_path, database_path=database_path)

    assert collection.is_collection_file(database_path) is True


def test_is_collection_file_rejects_other_paths(tmp_path: Path) -> None:
    database_path = tmp_path / "vacation.prismic"
    database_path.touch()
    collection = Collection(root=tmp_path, database_path=database_path)

    assert collection.is_collection_file(tmp_path / "photo.jpg") is False
