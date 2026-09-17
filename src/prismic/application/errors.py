"""Application-layer command validation errors.

Distinct from `persistence.errors`: these are precondition failures in a
command's *validate* step (e.g. an already-selected filter tag), not
persistence-layer or SQL-level failures.
"""

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for command-level validation errors."""


class UnknownMappingError(ApplicationError):
    def __init__(self, media_id: int, tag_id: int) -> None:
        super().__init__(f"No mapping between media {media_id} and tag {tag_id}")
        self.media_id = media_id
        self.tag_id = tag_id


class TagAlreadySelectedError(ApplicationError):
    def __init__(self, tag_id: int) -> None:
        super().__init__(f"Tag {tag_id} is already part of the active filter")
        self.tag_id = tag_id


class TagNotSelectedError(ApplicationError):
    def __init__(self, tag_id: int) -> None:
        super().__init__(f"Tag {tag_id} is not part of the active filter")
        self.tag_id = tag_id
