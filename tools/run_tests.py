"""Driver for the "not-slow-by-default" test-running policy.

`@pytest.mark.slow` tests (5+ seconds each -- see the marker definition in
pyproject.toml) are excluded from the default run. This script decides
which of them to run this time by unioning two sources, per
`development documents/owned by human/testing flow.md`:

- `--relevant <nodeid>...`: tests Claude judged relevant to what changed.
- Staleness: any slow test not run in the last 24h (or never run), read
  from `.slow_test_state.json` (gitignored; written automatically by
  tests/conftest.py's pytest_runtest_logreport hook whenever a slow test
  actually runs, however it was invoked).

Either condition alone is enough to include a test -- this is a union,
not an intersection.

Usage:
    uv run python tools/run_tests.py                      # not-slow + stale slow tests
    uv run python tools/run_tests.py --relevant tests/a.py::test_x tests/b.py::test_y
    uv run python tools/run_tests.py --all-slow            # force every slow test
    uv run python tools/run_tests.py --audit               # print staleness/demotion status
    uv run python tools/run_tests.py -- tests/unit         # extra args after `--` go to pytest
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import TypedDict


class _SlowTestEntry(TypedDict):
    last_run: float
    recent_durations: list[float]


ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / ".slow_test_state.json"
STALE_AFTER_SECONDS = 24 * 60 * 60
DEMOTION_THRESHOLD_SECONDS = 5.0
DEMOTION_STREAK = 3


def _load_state() -> dict[str, _SlowTestEntry]:
    try:
        result: dict[str, _SlowTestEntry] = json.loads(STATE_PATH.read_text())
        return result
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _slow_nodeids() -> list[str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "slow", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        line
        for line in result.stdout.splitlines()
        if "::" in line and not line.startswith((" ", "="))
    ]


def _stale_slow_tests(all_slow: list[str]) -> list[str]:
    state = _load_state()
    now = time.time()
    stale = []
    for nodeid in all_slow:
        entry = state.get(nodeid)
        last_run = entry["last_run"] if entry is not None else 0.0
        if now - last_run > STALE_AFTER_SECONDS:
            stale.append(nodeid)
    return stale


def audit() -> None:
    state = _load_state()
    now = time.time()
    for nodeid in _slow_nodeids():
        entry = state.get(nodeid)
        if entry is None:
            print(f"{'never run':>12}  {nodeid}")
            continue
        age_hours = (now - entry["last_run"]) / 3600
        durations = entry["recent_durations"]
        demotable = len(durations) >= DEMOTION_STREAK and all(
            d < DEMOTION_THRESHOLD_SECONDS for d in durations[-DEMOTION_STREAK:]
        )
        flag = "  <-- consider removing @pytest.mark.slow" if demotable else ""
        print(f"{age_hours:9.1f}h ago  {durations}  {nodeid}{flag}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--relevant",
        nargs="*",
        default=[],
        metavar="NODEID",
        help="slow test nodeids judged relevant to what changed this session",
    )
    parser.add_argument("--all-slow", action="store_true", help="force every slow test to run")
    parser.add_argument(
        "--audit",
        action="store_true",
        help="print each slow test's staleness and demotion status; run nothing",
    )
    parser.add_argument(
        "pytest_args", nargs="*", help="extra args passed through to the not-slow pytest call"
    )
    args = parser.parse_args()

    if args.audit:
        audit()
        return

    fast_run = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "-m", "not slow", *args.pytest_args],
        cwd=ROOT,
    )

    all_slow = _slow_nodeids()
    if args.all_slow:
        selection = all_slow
    else:
        selection = sorted(set(args.relevant) | set(_stale_slow_tests(all_slow)))

    slow_returncode = 0
    if selection:
        print(f"\nRunning {len(selection)} slow test(s) (relevant-or-stale selection):")
        for nodeid in selection:
            print(f"  {nodeid}")
        print()
        slow_run = subprocess.run([sys.executable, "-m", "pytest", "-v", *selection], cwd=ROOT)
        slow_returncode = slow_run.returncode
    else:
        print("\nNo slow tests judged relevant or stale -- skipping the slow pool.")

    sys.exit(fast_run.returncode or slow_returncode)


if __name__ == "__main__":
    main()
