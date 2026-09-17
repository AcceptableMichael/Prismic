"""CRUD access to the `tags` table."""

from __future__ import annotations

import sqlite3

from prismic.domain.tag import Tag, validate_tag_name
from prismic.persistence.errors import DuplicateTagNameError, UnknownTagError


class TagRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(self, name: str) -> Tag:
        validated = validate_tag_name(name)
        try:
            cursor = self._connection.execute("INSERT INTO tags (name) VALUES (?)", (validated,))
        except sqlite3.IntegrityError as exc:
            raise DuplicateTagNameError(validated) from exc
        tag_id = cursor.lastrowid
        assert tag_id is not None
        return Tag(id=tag_id, name=validated)

    def rename(self, tag_id: int, new_name: str) -> Tag:
        validated = validate_tag_name(new_name)
        try:
            cursor = self._connection.execute(
                "UPDATE tags SET name = ? WHERE id = ?", (validated, tag_id)
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateTagNameError(validated) from exc
        if cursor.rowcount == 0:
            raise UnknownTagError(tag_id)
        return Tag(id=tag_id, name=validated)

    def delete(self, tag_id: int) -> None:
        self._connection.execute("DELETE FROM media_tags WHERE tag_id = ?", (tag_id,))
        cursor = self._connection.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        if cursor.rowcount == 0:
            raise UnknownTagError(tag_id)

    def get(self, tag_id: int) -> Tag | None:
        row = self._connection.execute(
            "SELECT id, name FROM tags WHERE id = ?", (tag_id,)
        ).fetchone()
        return Tag(id=row["id"], name=row["name"]) if row is not None else None

    def list_all(self) -> list[Tag]:
        rows = self._connection.execute("SELECT id, name FROM tags ORDER BY name").fetchall()
        return [Tag(id=row["id"], name=row["name"]) for row in rows]
