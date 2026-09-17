"""The Collection domain type: an opened collection's identity on disk."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Collection:
    """An opened collection: its media root and its single `.prismic` file.

    `database_path` always sits directly inside `root` per the single-file
    collection design (see requirements-amendments.md) and is excluded from
    media discovery by exact path match.
    """

    root: Path
    database_path: Path

    def is_collection_file(self, path: Path) -> bool:
        """Whether `path` is this collection's own `.prismic` file."""
        return path.resolve() == self.database_path.resolve()
