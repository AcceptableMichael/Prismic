from pathlib import Path

import pytest

from prismic.persistence.errors import CollectionLockedError
from prismic.persistence.lockfile import CollectionLock


def test_acquire_and_release_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "vacation.prismic"
    target.touch()
    lock = CollectionLock(target)

    lock.acquire()
    lock.release()  # should not raise


def test_a_second_lock_on_the_same_file_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "vacation.prismic"
    target.touch()
    first = CollectionLock(target)
    first.acquire()
    try:
        second = CollectionLock(target)
        with pytest.raises(CollectionLockedError):
            second.acquire()
    finally:
        first.release()


def test_after_release_another_lock_can_be_acquired(tmp_path: Path) -> None:
    target = tmp_path / "vacation.prismic"
    target.touch()
    first = CollectionLock(target)
    first.acquire()
    first.release()

    second = CollectionLock(target)
    second.acquire()
    second.release()


def test_context_manager_releases_on_exit(tmp_path: Path) -> None:
    target = tmp_path / "vacation.prismic"
    target.touch()

    with CollectionLock(target):
        pass

    second = CollectionLock(target)
    second.acquire()
    second.release()
