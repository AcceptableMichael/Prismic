"""Content hashing for media identity comparisons.

A pure function with no Qt/GUI dependency, safe to call from any thread —
the worker pool that actually dispatches it off the GUI thread is Phase 3's
`PrismicSession` responsibility (see overview section 7).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1 << 20  # 1 MiB


def hash_file(path: Path) -> str:
    """The content hash of `path`, used consistently for identity comparisons.

    Raises `OSError` (e.g. `PermissionError`) if the file can't be read —
    callers are responsible for treating that as "unreadable, skip" rather
    than letting it abort a whole reconciliation pass.
    """
    digest = hashlib.blake2b()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()
