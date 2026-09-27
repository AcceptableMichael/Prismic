# Testing flow

After you make changes, you may decide it's appropriate to run a suite of
tests, beyond "computer use", to test the new thing that you're building.

pytest-qt tests should be comprehensive. You should add / modify them as you
go. This is a UI-heavy application, so these will probably be the basis of
most automated testing. You may want to track the time duration it takes to
run these tests, in order to balance comprehensiveness vs. reality.

Code/logic unit tests should cover things as you feel appropriate.

## When to run them

Verification happens in this order, and **all three must be done before
a task is considered complete**:

1. **Targeted `pytest`** — the tests covering what you just built, and
   whatever else you judge relevant. Write them as you go; run them as
   you go. This is the fast loop.
2. **Computer use** — actually look at the running app and exercise the
   thing. Tests can't see rendering, real focus routing, or a click
   that re-enters a model mid-event; this project has a history of bugs
   that only showed up here.
3. **The full `pytest` suite** — the regression net over everything
   else, run once the work is otherwise done. Run it via
   `uv run python tools/run_tests.py` rather than bare `pytest`: some
   tests are marked `slow` (5+ seconds) and excluded from a plain run —
   see "Slow tests" below for what still gets them run.

## Slow tests

A handful of tests (2000-file/5000-record stress cases, currently) take
5+ seconds each and are marked `@pytest.mark.slow`. They're excluded
from a default `pytest` invocation so the normal loop stays fast, but
skipping them silently forever would let a real regression sit
undetected for arbitrarily long — so `tools/run_tests.py` still runs a
slow test whenever **either** of these is true:

- **Relevance** — Claude judges the test relevant to what changed this
  session, and passes its nodeid via `--relevant`.
- **Staleness** — the test hasn't been run in the last 24 hours (or has
  never been run), tracked in the gitignored `.slow_test_state.json`.

Either condition alone is enough; this is a union, not an intersection.
Claude audits the slow-test pool as part of running tests (see
[`project guidance.md`](../owned%20by%20claude/project%20guidance.md))
— both for tests that should be added to it, and for ones that no
longer earn their `slow` mark.

The ordering is about cost and about what each step can catch: the
cheapest feedback first, then the things only a real window reveals,
then the slow sweep. Don't spend a manual pass on code the targeted
tests would have failed, and don't pay for the full suite on every
iteration — it takes minutes, so inside an edit/fix loop it is mostly
waiting rather than verifying.

These are gates, not a one-way pipeline. If step 2 or 3 turns something
up, fix it and come back through step 1 — the order still holds on the
way back out.

`ruff` and `mypy` sit outside this list: they're fast, they catch a
different class of problem (a rename that missed a call site, an unused
import), and they should be running throughout rather than waiting for
a gate.
