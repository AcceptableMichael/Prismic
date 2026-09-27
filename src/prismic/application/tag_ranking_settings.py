"""App-wide, user-configurable thresholds for `tag_ranking.promote_ranked_tags`.

App-wide rather than per-collection, and persisted the same way as
`ShortcutBindings` -- via `PreferencesStore`, under its own key so
neither settings group has to know the other's shape.
"""

from __future__ import annotations

from dataclasses import dataclass

from prismic.persistence.preferences import PreferencesStore

_PREFERENCES_KEY = "tag_ranking"

DEFAULT_CORRELATION_THRESHOLD = 0.80
"""Y must appear on at least this fraction of X's files to be promoted
when X is checked -- the product's own ">=80%" default."""

DEFAULT_MEGA_POPULAR_THRESHOLD = 0.15
"""A tag present on at least this fraction of the whole collection is
"mega popular" and promoted regardless of what's checked."""


@dataclass(frozen=True, slots=True)
class TagRankingSettings:
    correlation_threshold: float = DEFAULT_CORRELATION_THRESHOLD
    mega_popular_threshold: float = DEFAULT_MEGA_POPULAR_THRESHOLD


def _as_fraction(value: object, default: float) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool) and 0.0 <= value <= 1.0:
        return float(value)
    return default


class TagRankingSettingsStore:
    def __init__(self, store: PreferencesStore | None = None) -> None:
        self._store = store if store is not None else PreferencesStore()

    def load(self) -> TagRankingSettings:
        raw = self._store.load().get(_PREFERENCES_KEY)
        if not isinstance(raw, dict):
            return TagRankingSettings()
        return TagRankingSettings(
            correlation_threshold=_as_fraction(
                raw.get("correlation_threshold"), DEFAULT_CORRELATION_THRESHOLD
            ),
            mega_popular_threshold=_as_fraction(
                raw.get("mega_popular_threshold"), DEFAULT_MEGA_POPULAR_THRESHOLD
            ),
        )

    def save(self, settings: TagRankingSettings) -> None:
        data = self._store.load()
        data[_PREFERENCES_KEY] = {
            "correlation_threshold": settings.correlation_threshold,
            "mega_popular_threshold": settings.mega_popular_threshold,
        }
        self._store.save(data)
