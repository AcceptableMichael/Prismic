import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from prismic.domain.collection import Collection
from prismic.indexing.scanner import scan


def _collection(root: Path) -> Collection:
    return Collection(root=root, database_path=root / "test.prismic")


def test_finds_supported_files_recursively(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"1")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.png").write_bytes(b"2")

    found = {f.relative_path for f in scan(_collection(tmp_path))}

    assert found == {"a.jpg", "nested/b.png"}


def test_excludes_unsupported_extensions(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"1")
    (tmp_path / "notes.txt").write_bytes(b"not media")

    found = {f.relative_path for f in scan(_collection(tmp_path))}

    assert found == {"a.jpg"}


def test_excludes_the_collections_own_database_file(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"1")
    collection = _collection(tmp_path)
    collection.database_path.touch()

    found = {f.relative_path for f in scan(collection)}

    assert found == {"a.jpg"}


def test_reports_size_and_mtime(tmp_path: Path) -> None:
    target = tmp_path / "a.jpg"
    target.write_bytes(b"some bytes")

    (found,) = list(scan(_collection(tmp_path)))

    assert found.size == target.stat().st_size
    assert found.mtime == target.stat().st_mtime


def test_continues_past_an_unreadable_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    good = tmp_path / "good"
    bad = tmp_path / "bad"
    good.mkdir()
    bad.mkdir()
    (good / "a.jpg").write_bytes(b"1")
    (bad / "b.jpg").write_bytes(b"2")

    real_scandir = os.scandir

    def _flaky_scandir(path: str | os.PathLike[str]) -> Iterator[os.DirEntry[str]]:
        if Path(path) == bad:
            raise PermissionError("simulated permission failure")
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", _flaky_scandir)

    found = {f.relative_path for f in scan(_collection(tmp_path))}

    assert found == {"good/a.jpg"}


def test_does_not_follow_a_symlinked_directory(tmp_path: Path) -> None:
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "inside.jpg").write_bytes(b"1")
    (tmp_path / "outside.jpg").write_bytes(b"2")

    link = tmp_path / "link"
    _make_directory_link_or_skip(link, real_dir)

    found = {f.relative_path for f in scan(_collection(tmp_path))}

    assert found == {"outside.jpg", "real/inside.jpg"}
    assert not any(path.startswith("link/") for path in found)


def _make_directory_link_or_skip(link: Path, target: Path) -> None:
    if sys.platform == "win32":
        # Junctions don't require elevated privileges on Windows, unlike
        # symlinks, and are the reparse-point case the overview specifically
        # calls out ("does not follow Windows junctions/reparse points").
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            pytest.skip(f"could not create a junction in this environment: {result.stderr!r}")
    else:
        try:
            os.symlink(target, link, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f"could not create a symlink in this environment: {exc}")
