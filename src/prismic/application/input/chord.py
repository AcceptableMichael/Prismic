"""A chorded-shortcut state machine, independent of any widget or timer.

A chord is a sequence of key presses that together resolve to a single
command (e.g. "g g", or "Ctrl+K Ctrl+S"). Phase 5 drives `advance_time()`
with a real `QTimer`; this module only tracks pending keys and cancellation/
timeout behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChordState:
    timeout_seconds: float = 1.0
    _pending_keys: list[str] = field(default_factory=list, init=False, repr=False)
    _elapsed_since_last_key: float = field(default=0.0, init=False, repr=False)

    @property
    def is_pending(self) -> bool:
        return bool(self._pending_keys)

    @property
    def pending_keys(self) -> tuple[str, ...]:
        return tuple(self._pending_keys)

    def press(self, key: str) -> None:
        self._pending_keys.append(key)
        self._elapsed_since_last_key = 0.0

    def advance_time(self, seconds: float) -> bool:
        """Advance the chord's clock since the last key press.

        Returns True if this caused the pending chord to time out and
        cancel (no key pressed within `timeout_seconds`). A no-op, always
        returning False, when no chord is in progress.
        """
        if not self._pending_keys:
            return False
        self._elapsed_since_last_key += seconds
        if self._elapsed_since_last_key >= self.timeout_seconds:
            self.cancel()
            return True
        return False

    def cancel(self) -> None:
        self._pending_keys.clear()
        self._elapsed_since_last_key = 0.0

    def match(self, chords: dict[tuple[str, ...], str]) -> str | None:
        """Check `pending_keys` against a table of complete chords.

        Returns the matched command name (and clears the pending state) on
        an exact match. Returns None, leaving the pending state alone, if
        the current keys are still a valid *prefix* of some registered
        chord — more keys could still complete it. Returns None and
        cancels if the current keys are a dead end (a prefix of nothing
        registered).
        """
        current = tuple(self._pending_keys)
        if current in chords:
            self.cancel()
            return chords[current]
        if not any(candidate[: len(current)] == current for candidate in chords):
            self.cancel()
        return None
