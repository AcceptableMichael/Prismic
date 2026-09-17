# Phase 5 — UI & viewer

Goal: the real application UI, built on Qt model/view abstractions, wired
entirely through the Phase 3 application layer — no widget implements
persistence or undo itself. Corresponds to overview sections 2, 6, 10, 11,
and replaces the Phase 0 placeholder window.

## Main window & wiring

- [ ] Replace the placeholder keycap/background-demo content in
      `main_window.py` with the real layout (tag panel, result view, viewer)
- [ ] Main window opens a collection (directory picker) and constructs a
      `PrismicSession` through the Phase 1/3 lifecycle, handling the
      failed-open case visibly instead of silently
- [ ] No widget talks to the database or filesystem directly — everything
      goes through application-layer commands/queries

## Tag & filter UI

- [ ] Tag list view backed by a Qt model (not manually rebuilt widget lists)
      for scale
- [ ] Create / rename / delete tags from the UI, dispatched as Phase 3
      commands
- [ ] Multi-select tag filter UI; selection dispatches filter
      selection/deselection commands
- [ ] Filter UI reflects the recalculated result set live as selection
      changes

## Result view

- [ ] Result list/grid backed by a Qt model reflecting the current query
      result set and its deterministic ordering
- [ ] Arrow-key navigation through results, respecting the current-item
      invariant from Phase 3
- [ ] Stays responsive while the result set changes underneath it (no full
      rebuild-and-flicker on every keystroke of a filter change)

## Media viewer

- [ ] Image display with zoom, scroll/pan, double-click-to-zoom, and other
      conventional viewer interactions
- [ ] Video playback with play/pause, seeking, and navigation between items
      without leaving the viewer
- [ ] Tag mappings for the currently displayed item are editable in place,
      without leaving the viewer
- [ ] Viewer stays responsive during navigation and interaction (backed by
      Phase 4's caching/staleness work)

## Keyboard input layer (`ui/` wiring onto `application/input/`)

- [ ] Central input dispatcher implements the precedence order: text-editing
      context → local/modal interaction → viewer interaction → global
      application command
- [ ] Chorded shortcuts wired to the Phase 3 cancellation/timeout state
      machine
- [ ] Common tag/mapping operations (create tag, apply tag, remove tag,
      navigate) are reachable via keyboard alone, without refocusing a mouse
      control
- [ ] UI state updates in realtime as the user types/chords, not just on
      commit

## Tests (`tests/gui`, pytest-qt)

- [ ] Tag CRUD via the UI
- [ ] Filter selection/deselection via the UI and resulting view updates
- [ ] Keyboard navigation through results (arrow keys), including the
      current-item invariant when the set changes under the user
- [ ] Chorded shortcut sequences, including cancellation/timeout
- [ ] In-viewer tag editing without leaving the viewer
- [ ] Viewer zoom/pan/double-click and video play/pause/seek interactions
- [ ] Computer-use pass (see `project guidance.md` launch-path note) over
      the primary keyboard-driven tagging workflow, not just automated tests
