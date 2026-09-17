"""Domain-level persistence errors.

Repositories and the collection lifecycle raise these instead of letting raw
sqlite3 exceptions or filesystem details leak past the persistence layer.
"""

from __future__ import annotations

from pathlib import Path


class PersistenceError(Exception):
    """Base class for all persistence-layer errors."""


class DuplicateTagNameError(PersistenceError):
    def __init__(self, name: str) -> None:
        super().__init__(f"A tag named {name!r} already exists")
        self.name = name


class DuplicateMappingError(PersistenceError):
    def __init__(self, media_id: int, tag_id: int) -> None:
        super().__init__(f"Media {media_id} is already mapped to tag {tag_id}")
        self.media_id = media_id
        self.tag_id = tag_id


class UnknownTagError(PersistenceError):
    def __init__(self, tag_id: int) -> None:
        super().__init__(f"No tag with id {tag_id}")
        self.tag_id = tag_id


class UnknownMediaError(PersistenceError):
    def __init__(self, media_id: int) -> None:
        super().__init__(f"No media with id {media_id}")
        self.media_id = media_id


class SchemaMigrationError(PersistenceError):
    """A migration failed; the schema was rolled back to its prior version."""


class IncompatibleDatabaseError(PersistenceError):
    """The `.prismic` file exists but is not a readable Prismic database.

    Raised instead of silently replacing an unreadable/incompatible database
    with a new empty one.
    """

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path} is not a valid Prismic collection database: {reason}")
        self.path = path
        self.reason = reason


class SchemaTooNewError(PersistenceError):
    """The database's schema version is newer than this build supports."""

    def __init__(self, path: Path, found_version: int, supported_version: int) -> None:
        super().__init__(
            f"{path} uses schema version {found_version}, "
            f"but this build only supports up to {supported_version}"
        )
        self.path = path
        self.found_version = found_version
        self.supported_version = supported_version


class MultipleCollectionFilesError(PersistenceError):
    """More than one `*.prismic` file was found at a collection root."""

    def __init__(self, directory: Path, matches: list[Path]) -> None:
        super().__init__(
            f"Found {len(matches)} .prismic files in {directory}, expected at most one: "
            + ", ".join(str(match) for match in matches)
        )
        self.directory = directory
        self.matches = matches


class CollectionLockedError(PersistenceError):
    """The collection's `.prismic` file is already locked by another instance."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Collection is already open elsewhere: {path}")
        self.path = path
