"""CRUD access to the `media_tags` mapping table."""

from __future__ import annotations

import sqlite3

from prismic.domain.tag import Tag
from prismic.persistence.errors import DuplicateMappingError


class MappingRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, media_id: int, tag_id: int) -> None:
        """Map `media_id` to `tag_id`.

        Raises `DuplicateMappingError` if the mapping already exists. A
        reference to a nonexistent media or tag id is a foreign-key
        violation and propagates as a raw `sqlite3.IntegrityError` — that's
        a programming error in the caller, not a recoverable domain case.
        """
        try:
            self._connection.execute(
                "INSERT INTO media_tags (media_id, tag_id) VALUES (?, ?)", (media_id, tag_id)
            )
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed" in str(exc):
                raise DuplicateMappingError(media_id, tag_id) from exc
            raise

    def remove(self, media_id: int, tag_id: int) -> None:
        self._connection.execute(
            "DELETE FROM media_tags WHERE media_id = ? AND tag_id = ?", (media_id, tag_id)
        )

    def tags_for_media(self, media_id: int) -> list[Tag]:
        rows = self._connection.execute(
            """
            SELECT tags.id, tags.name
            FROM tags
            JOIN media_tags ON media_tags.tag_id = tags.id
            WHERE media_tags.media_id = ?
            ORDER BY tags.name
            """,
            (media_id,),
        ).fetchall()
        return [Tag(id=row["id"], name=row["name"]) for row in rows]

    def media_ids_for_tags(self, tag_ids: list[int]) -> list[int]:
        """Ids of media mapped to *every* tag in `tag_ids` (intersection)."""
        if not tag_ids:
            return []
        placeholders = ",".join("?" for _ in tag_ids)
        rows = self._connection.execute(
            f"""
            SELECT media_id
            FROM media_tags
            WHERE tag_id IN ({placeholders})
            GROUP BY media_id
            HAVING COUNT(DISTINCT tag_id) = ?
            """,
            (*tag_ids, len(tag_ids)),
        ).fetchall()
        return [row["media_id"] for row in rows]
