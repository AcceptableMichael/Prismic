# Phase 3 — Application layer

Goal: every user-visible mutation and query goes through one command/query
layer that owns state, undo, and filter semantics, so the UI (Phase 5) never
has to implement product logic itself. Corresponds to overview sections 1,
4 (relational parts), 5, and the non-media parts of section 7.

## Session assembly (`application/session.py`)

- [x] `PrismicSession` composes: collection root, database, repositories,
      application state, command dispatcher, undo history, filesystem
      reconciler handle, worker pool. ("Media services handle" is omitted —
      there's nothing to hold a handle *to* yet; Phase 4 adds it.)
- [x] Only one session is active at a time in the process (a usage
      discipline, not enforced by a singleton — nothing in this codebase
      opens two)
- [x] Session construction/teardown matches the open/close lifecycle from
      Phase 1 (no partially-built session on failure) — delegated directly
      to `persistence.collection.open_collection`, which already guarantees
      this

**Closing Phase 2's deferred background-execution items:** `PrismicSession`
now actually dispatches the initial scan/reconcile (and any `rescan()`) onto
`WorkerPool`, a plain `concurrent.futures.ThreadPoolExecutor` wrapper
(`application/worker_pool.py`) — deliberately not Qt's `QThreadPool`, so the
application layer stays Qt-free per the architecture's layer boundaries.
Each background task opens **its own** connection to the `.prismic` file
(`persistence.database.connect`) rather than reusing the session's
main-thread connection, per overview section 7's "connections are owned by
their execution context" rule — this is why `indexing.reconciler.Reconciler`
was reshaped in this phase to take a connection *per call* instead of
owning one (see the Phase 2 file's changelog note). `Reconciler`'s
generation counter and reconcile-and-commit sequence are guarded by an
internal lock so overlapping calls from different threads can't interleave.

One thing this phase deliberately does **not** do: automatically refresh
`state` when a background reconciliation completes. A `Future`'s
done-callback runs on the *worker* thread, and `state.recompute()` needs the
main-thread repositories — safely marshaling "the scan finished" back onto
the main/GUI thread is Phase 5's job (a queued Qt signal, once there's a Qt
event loop to queue onto). For now, callers explicitly call
`session.refresh_state()` themselves after observing
`session.initial_reconciliation` / `session.rescan()`'s future complete.

## State (`application/state.py`)

- [x] Holds current filter (selected tag ids), current result set, current
      item
- [x] Invariant enforced at every state transition: `current_item` is either
      `null` or a member of the active result set
- [x] When the current item leaves the result set: select the nearest
      surviving item in the previous navigation order; if none survives,
      select the first result; if there are no results, `current_item` is
      `null`. ("Nearest" ties are broken toward the following item, not the
      preceding one — documented in code, not specified by the overview.)

Note: if `current_item` was already `null`, it *stays* `null` even once a
non-empty result set appears — the "leaves the result set" recovery logic
only fires when a previously-valid selection is invalidated, not to
auto-select something the user never chose. `null` is always a legal value
per the invariant as written.

## Commands (`application/commands/`)

- [x] Common command shape following: validate → begin transaction → mutate
      database → commit → publish new application state; a failed
      transaction publishes no partial state. Implemented as `Command`
      (`execute`/`undo`) + `CommandDispatcher`, which wraps both in a
      transaction and only calls `state.recompute()` / pushes to history
      after a successful commit.
- [x] Tag creation
- [x] Tag rename
- [x] Tag deletion (and its effect on existing mappings — cascades removing
      `media_tags` rows, and removes the tag from the active filter if it
      was selected)
- [x] Mapping creation (file↔tag)
- [x] Mapping deletion
- [x] Filter selection / deselection (tag added to/removed from the active
      filter) — undoable too, per overview section 7
- [x] Every mapping written always references an existing media id and tag
      id — validated explicitly in `MappingAddCommand.execute` (not just
      relying on the FK constraint to reject it after the fact)

**Design note — tag delete/undo and id reuse:** `TagDeleteCommand.undo()`
recreates the tag and its mappings, but necessarily as a **new** tag id —
ids aren't reused across a delete/create round trip (the `tags`/`media`
tables use `AUTOINCREMENT` specifically so they never are, even after the
table empties out; SQLite recycles bare `INTEGER PRIMARY KEY` rowids by
default, which would otherwise silently reattach history to the wrong
identity). This is safe under the undo stack's strict LIFO discipline: by
the time a `TagDeleteCommand` is undone, any later command that referenced
the tag's old id would already have been undone first.

## Undo (`application/history.py`)

- [x] Session-local undo history; cleared on restart (no persistence —
      it's just a Python list, never written to the database)
- [x] Every command above is undoable
- [x] Undo operates on logical actions, not low-level events — each command
      instance captures exactly what it needs at `execute()` time to
      reverse itself in one `undo()` call
- [x] Multiple sequential undos work correctly (stack discipline)
- [x] Redo is explicitly out of scope for v1 — not built
- [x] External filesystem changes (from the Phase 2 reconciler) are
      observed and reflected in state (via `refresh_state()`) but are never
      undoable — the reconciler has no undo path at all, by construction

## Queries (`application/queries/`)

- [x] Zero selected tags → all discovered (active) supported media eligible
- [x] One tag, multiple tags → correct intersection semantics
- [x] Empty intersection → empty result set, not an error
- [x] Deterministic ordering: normalized relative path, ascending
- [x] Result set recalculates correctly as tags are selected/deselected
      (`ApplicationState.recompute`, called by the dispatcher after every
      command)
- [x] Scales acceptably on a large result set — a rough smoke-test
      benchmark (5,000 media rows, asserts well under 2s) catches a gross
      regression like an accidental N+1 query; not a real perf target

## Input layer scaffolding (`application/input/`)

- [x] Command-resolution precedence data structures (`InputContext`,
      `INPUT_CONTEXT_PRECEDENCE`, `InputResolver`) — actual Qt keyboard
      wiring is still Phase 5's job; this only defines the resolution order
      and a Qt-independent dispatch mechanism
- [x] Chorded shortcut state machine (`ChordState`) with explicit
      cancellation/timeout, independent of any widget or real timer —
      `advance_time()` is driven by whatever clock the caller has (a real
      `QTimer` in Phase 5, a plain float in tests)

## Tests (`tests/unit`, `tests/integration`)

- [x] Tag creation / rename / deletion
- [x] Mapping creation / deletion
- [x] Filter selection / deselection
- [x] Undo, and multiple undo, for every command above
- [x] Core invariant: `execute(command)` always yields a valid state
- [x] Core invariant: `execute(command)` then `undo` restores the original
      state
- [x] Core invariant: every mapping references an existing media and tag
- [x] Core invariant: `current_media == null OR current_media ∈ active_result_set`
- [x] Core invariant: failed persistence publishes no partial mutation
- [x] Query tests: zero/one/multiple tags, empty intersection, deterministic
      ordering, large result set
