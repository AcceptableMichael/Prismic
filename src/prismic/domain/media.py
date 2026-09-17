"""The Media domain type: a logical media identity within a collection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MediaState(StrEnum):
    """Lifecycle state of a media identity relative to the filesystem.

    Reconciliation (Phase 2) is what actually transitions media between
    these states; this enum only names the states the domain recognizes.
    """

    ACTIVE = "active"
    """The recorded relative_path currently resolves to matching content."""

    MISSING = "missing"
    """No file on disk currently accounts for this identity (moved away
    with no unique match found, or its content changed at that path)."""


@dataclass(frozen=True, slots=True)
class Media:
    """A media file's identity, independent of its current filesystem path.

    `id` is the stable identity that tag mappings reference. `content_hash`
    is content evidence used for move/replacement detection, not identity
    itself. `relative_path` is relative to the owning collection's root.
    """

    id: int
    relative_path: str
    content_hash: str
    size: int
    mtime: float
    state: MediaState
