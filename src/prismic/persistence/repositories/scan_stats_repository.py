"""Access to the `scan_stats` singleton row.

Holds the file count observed by the most recently *completed* scan, so the
*next* scan has something to use as a progress denominator -- a scan in
progress can't know its own total ahead of time (see
`indexing.reconciler.run_reconciliation`), so the best available estimate is
however many candidate files the collection held last time.
"""

from __future__ import annotations

import sqlite3


class ScanStatsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_last_file_count(self) -> int:
        row = self._connection.execute("SELECT last_file_count FROM scan_stats WHERE id = 1").fetchone()
        assert row is not None  # the singleton row is seeded by migration, never absent
        return int(row["last_file_count"])

    def set_last_file_count(self, count: int) -> None:
        self._connection.execute("UPDATE scan_stats SET last_file_count = ? WHERE id = 1", (count,))
