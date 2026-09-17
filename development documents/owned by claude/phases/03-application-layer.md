# Phase 3 — Application layer

Goal: every user-visible mutation and query goes through one command/query
layer that owns state, undo, and filter semantics, so the UI (Phase 5) never
has to implement product logic itself. Corresponds to overview sections 1,
4 (relational parts), 5, and the non-media parts of section 7.

## Session assembly (`application/session.py`)

- [ ] `PrismicSession` composes: collection root, database, repositories,
      application state, command dispatcher, undo history, filesystem
      reconciler handle, media services handle, worker pool
- [ ] Only one session is active at a time in the process
- [ ] Session construction/teardown matches the open/close lifecycle from
      Phase 1 (no partially-built session on failure)

## State (`application/state.py`)

- [ ] Holds current filter (selected tag ids), current result set, current
      item
- [ ] Invariant enforced at every state transition: `current_item` is either
      `null` or a member of the active result set
- [ ] When the current item leaves the result set: select the nearest
      surviving item in the previous navigation order; if none survives,
      select the first result; if there are no results, `current_item` is
      `null`

## Commands (`application/commands/`)

- [ ] Common command shape following: validate → begin transaction → mutate
      database → commit → publish new application state; a failed
      transaction publishes no partial state
- [ ] Tag creation
- [ ] Tag rename
- [ ] Tag deletion (and its effect on existing mappings)
- [ ] Mapping creation (file↔tag)
- [ ] Mapping deletion
- [ ] Filter selection / deselection (tag added to/removed from the active
      filter) — this is undoable too, per overview section 7
- [ ] Every mapping written always references an existing media id and tag
      id (enforce, don't just assume)

## Undo (`application/history.py`)

- [ ] Session-local undo history; cleared on restart (no persistence)
- [ ] Every command above is undoable
- [ ] Undo operates on logical actions, not low-level events — e.g. a
      completed tag rename is one undo step, not one per keystroke
- [ ] Multiple sequential undos work correctly (stack discipline)
- [ ] Redo is explicitly out of scope for v1 — don't build it
- [ ] External filesystem changes (from the Phase 2 reconciler) are observed
      and reflected in state but are never undoable

## Queries (`application/queries/`)

- [ ] Zero selected tags → all discovered supported media eligible
- [ ] One tag, multiple tags → correct intersection semantics
- [ ] Empty intersection → empty result set, not an error
- [ ] Deterministic ordering: normalized relative path, ascending
- [ ] Result set recalculates correctly as tags are selected/deselected
- [ ] Scales acceptably on a large result set (put a rough number on this
      once real data is available, e.g. via a benchmark fixture)

## Input layer scaffolding (`application/input/`)

- [ ] Define the command-resolution precedence data structures here (the
      actual Qt keyboard wiring is Phase 5): text-editing context → local/
      modal interaction → viewer interaction → global application command
- [ ] Chorded shortcut state machine with explicit cancellation/timeout,
      independent of any specific widget

## Tests (`tests/unit`, `tests/integration`)

- [ ] Tag creation / rename / deletion
- [ ] Mapping creation / deletion
- [ ] Filter selection / deselection
- [ ] Undo, and multiple undo, for every command above
- [ ] Core invariant: `execute(command)` always yields a valid state
- [ ] Core invariant: `execute(command)` then `undo` restores the original
      state
- [ ] Core invariant: every mapping references an existing media and tag
- [ ] Core invariant: `current_media == null OR current_media ∈ active_result_set`
- [ ] Core invariant: failed persistence publishes no partial mutation
- [ ] Query tests: zero/one/multiple tags, empty intersection, deterministic
      ordering, large result set
