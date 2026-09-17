"""Collection locking, verified across two genuinely separate OS processes
-- not just two objects in the same process (already covered at the unit
level in tests/integration/test_collection_lifecycle.py).
"""

import subprocess
import sys
from pathlib import Path

import pytest

from prismic.persistence.collection import open_collection
from prismic.persistence.errors import CollectionLockedError

_HOLD_LOCK_SCRIPT = """
import sys
from pathlib import Path
from prismic.persistence.collection import open_collection

opened = open_collection(Path(sys.argv[1]))
print("LOCKED", flush=True)
sys.stdin.readline()  # block until the parent test tells us to let go
opened.close()
"""


def test_a_second_process_cannot_open_a_collection_locked_by_the_first(tmp_path: Path) -> None:
    root = tmp_path / "vacation"
    root.mkdir()

    holder = subprocess.Popen(
        [sys.executable, "-c", _HOLD_LOCK_SCRIPT, str(root)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        line = holder.stdout.readline()
        assert line.strip() == "LOCKED", f"holder process didn't report locking: {line!r}"

        with pytest.raises(CollectionLockedError):
            open_collection(root)
    finally:
        assert holder.stdin is not None
        holder.stdin.write("\n")
        holder.stdin.close()
        holder.wait(timeout=10)

    # Once the other process releases it, opening works normally again.
    with open_collection(root) as reopened:
        assert reopened.collection.root == root
