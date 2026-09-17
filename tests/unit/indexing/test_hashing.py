from pathlib import Path

import pytest

from prismic.indexing.hashing import hash_file


def test_identical_content_produces_the_same_hash(tmp_path: Path) -> None:
    first = tmp_path / "a.jpg"
    second = tmp_path / "b.jpg"
    first.write_bytes(b"identical bytes")
    second.write_bytes(b"identical bytes")

    assert hash_file(first) == hash_file(second)


def test_different_content_produces_a_different_hash(tmp_path: Path) -> None:
    first = tmp_path / "a.jpg"
    second = tmp_path / "b.jpg"
    first.write_bytes(b"some content")
    second.write_bytes(b"different content")

    assert hash_file(first) != hash_file(second)


def test_hashes_content_larger_than_one_chunk(tmp_path: Path) -> None:
    large_file = tmp_path / "large.jpg"
    large_file.write_bytes(b"x" * (2 * (1 << 20) + 17))

    # Should not raise, and should be stable across repeated hashing.
    assert hash_file(large_file) == hash_file(large_file)


def test_an_unreadable_path_raises_os_error(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        hash_file(tmp_path)  # a directory can't be opened for reading as a file
