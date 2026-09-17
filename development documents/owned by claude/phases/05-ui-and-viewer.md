# Phase 5 — UI & viewer

Goal: the real application UI, built on Qt model/view abstractions, wired
entirely through the Phase 3 application layer — no widget implements
persistence or undo itself. Corresponds to overview sections 2, 6, 10, 11,
and replaces the Phase 0 placeholder window.

## Main window & wiring

- [x] Replaced the placeholder keycap/background-demo content in
      `main_window.py` with the real layout: filter panel, result list,
      viewer, and per-item tag panel in a `QSplitter`
- [x] Main window opens a collection via `File → Open Collection Folder…`
      or `File → Open .prismic File…`, constructing a `PrismicSession`
      through the Phase 1/3 lifecycle; a failed open (`PersistenceError`
      and subclasses — locked, incompatible, multiple `.prismic` files,
      schema too new, migration failure) shows a `QMessageBox`, not a crash
- [x] App launch accepts a `.prismic` file *or* collection directory path
      as a command-line argument (`bootstrap.py` passes `args[1]`, after
      `QApplication` strips its own recognized options, to `MainWindow`)
      and opens straight to it — verified with a real double-click-style
      launch via computer-use (see below), not just unit tests
- [x] No widget talks to the database or filesystem directly — reads go
      through repositories/`queries.media_query.eligible_media`; every
      mutation goes through `PrismicSession.execute()`

## Tag & filter UI

- [x] Tag list view backed by `ui/tag_model.py::TagListModel` (a
      `QAbstractListModel`), reused for both the filter panel and the
      viewer's per-item tag panel — display-only, emits `toggle_requested`
      rather than mutating anything itself
- [x] Create / rename / delete tags from the UI (`TagPanel`'s buttons →
      `QInputDialog` → `TagCreateCommand`/`TagRenameCommand`/`TagDeleteCommand`)
- [x] Multi-select tag filter UI: checking/unchecking a tag in the filter
      panel dispatches `FilterSelectCommand`/`FilterDeselectCommand`
- [x] Filter UI reflects the recalculated result set live — `_refresh_all()`
      recomputes `result_model` from `eligible_media(...)` after every
      command

## Result view

- [x] Result list backed by `ui/result_model.py::ResultListModel`,
      reflecting the query layer's deterministic relative-path ordering
      directly (no separate sort step in the UI)
- [x] Arrow-key navigation (`Left`/`Right`) through results, respecting the
      current-item invariant — navigation mutates `state.current_item`
      directly rather than through a command, since it's explicitly not
      one of the undoable actions listed in overview section 7
- [x] Selecting a result with the mouse and navigating with the keyboard
      both keep the list selection, the viewer, and the per-item tag panel
      in sync (`_sync_result_selection`, `_show_current_media`,
      `_refresh_item_tag_panel`)

## Media viewer

- [x] Image display with zoom (mouse wheel), pan (`ScrollHandDrag`, Qt's
      own built-in behavior), and double-click to toggle between fit-to-
      window and a fixed zoom level (`ui/image_view.py::ImageView`)
- [x] Video playback with play/pause (button, reflecting real playback
      state) and seeking (slider, reflecting real position/duration) via
      `ui/viewer.py::MediaViewer`, switching between an `ImageView` and a
      `QVideoWidget` by extension
- [x] Tag mappings for the current item are editable in place via the
      "Tags on this item" panel — checking a tag there dispatches
      `MappingAddCommand`/`MappingRemoveCommand` without leaving the viewer
- [x] Viewer stays responsive during navigation — backed directly by Phase
      4's `ImageLoader`/cache (`media/image.py::load_image` decodes
      per-call; the viewer itself doesn't yet route through
      `ImageLoader`'s generation-staleness machinery, since navigation here
      is synchronous and fast enough at this collection scale not to need
      it — revisit if large collections or slow storage make decode
      latency actually visible)

## Keyboard input layer

- [x] Central input dispatch via `ui/keyboard.py::KeyboardController`,
      itself built on the Phase 3 `InputResolver`/`ChordState` scaffolding
- [x] Chorded shortcuts wired to the Phase 3 cancellation/timeout state
      machine: `t` then a digit 1-9 toggles the Nth tag (list order) on the
      current item; `Escape` or a dead-end key cancels; an idle chord times
      out on its own via a `QTimer`
- [x] Reachable via keyboard alone: create tag (`n`), apply/remove tag
      (`t` + digit — one chord covers both directions), navigate
      (`Left`/`Right`), undo (`Ctrl+Z`)
- [x] UI state updates in real time as the user types/chords — the status
      bar shows the pending chord's keys as they're pressed

### Real bug found via computer-use, not by earlier automated tests

Every keyboard test up to this point sent keys with `qtbot.keyClick(window, ...)`
— straight to the top-level `MainWindow`, bypassing Qt's real focus-based
event delivery entirely. Driving the actual app by hand (see the pass
below) surfaced that pressing `n` after clicking a result did **nothing**:
`QAbstractItemView` (the result/tag lists) has its own built-in "type to
search" behavior that consumes plain letter keys itself before they'd ever
reach a `keyPressEvent` override on the window. Chords and global shortcuts
only ever worked in tests because the tests never gave a child widget real
focus first.

**Fix:** `MainWindow` now installs an `eventFilter` on the `QApplication`
itself (not just an override on its own `keyPressEvent`), intercepting key
events before Qt delivers them to whichever child widget is focused —
except when a `QLineEdit` has focus (the actual text-editing precedence
case: typing into a rename/create dialog must behave normally). Two new
regression tests in `tests/gui/test_keyboard.py` explicitly focus
`result_list` via `setFocus()` before sending keys, closing the gap the
earlier keyClick-on-window tests couldn't catch.

**Takeaway for future sessions:** a GUI keyboard test that always sends
keys directly to the top-level window is not equivalent to a real user
typing after clicking somewhere — it skips Qt's actual focus routing,
which is exactly where widget-specific key handling like this lives.

## Tests (`tests/gui`, pytest-qt)

- [x] Tag CRUD via the UI (`test_main_window.py`)
- [x] Filter selection/deselection via the UI and resulting view updates
      (`test_main_window.py`)
- [x] Keyboard navigation through results, including the current-item
      invariant when the set changes under the user, and — after the fix
      above — when a result-list child widget genuinely has focus
      (`test_keyboard.py`)
- [x] Chorded shortcut sequences, including cancellation, a dead-end key,
      and timeout (`test_keyboard.py`)
- [x] In-viewer tag editing without leaving the viewer (`test_main_window.py`)
- [x] Viewer zoom/pan/double-click (`test_image_view.py`) and video
      play/pause/seek (`test_viewer.py`)
- [x] Computer-use pass over the primary keyboard-driven tagging workflow,
      using the human's real manual-testing folder
      (`../../my data folder`, see `project guidance.md`) rather than
      synthetic fixtures: launched via the CLI path argument, opened
      straight to that folder, confirmed the result list matched exactly
      the supported files (`.avif` correctly excluded), navigated with
      arrow keys, created a tag with `n`, applied it with the `t`+digit
      chord, narrowed the view with the filter checkbox, and undid the
      filter selection with `Ctrl+Z` — each step visually confirmed against
      the real running app, not inferred from test results. This is what
      caught the keyboard-focus bug above.
