"""The Tag domain type and its name-validation rules."""

from __future__ import annotations

from dataclasses import dataclass


class InvalidTagNameError(ValueError):
    """A tag name fails the domain's validation rules."""


def validate_tag_name(name: str) -> str:
    """Validate a candidate tag name and return its stored (trimmed) form.

    Rules: non-empty after trimming, no newlines. Uniqueness and
    case-sensitivity are enforced by the persistence layer, not here, since
    they require checking against existing tags.
    """
    if "\n" in name or "\r" in name:
        raise InvalidTagNameError("Tag name must not contain newlines")
    trimmed = name.strip()
    if not trimmed:
        raise InvalidTagNameError("Tag name must not be empty")
    return trimmed


@dataclass(frozen=True, slots=True)
class Tag:
    """A user-defined tag. `id` is immutable; `name` is mutable (rename)."""

    id: int
    name: str
