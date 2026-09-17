# Phase 6 — Integration & hardening

Goal: all the layers built in Phases 1–5 work together as one coherent app
under realistic use, not just in isolation per-layer. This is where the
acceptance gates in overview section 13 get checked end-to-end rather than
per-component.

## End-to-end flows

- [x] Fresh directory → open as collection → initial scan/hash completes in
      the background → tags and media appear correctly, GUI usable
      throughout (`tests/integration/test_end_to_end.py`; the session is
      commandable *before* `initial_reconciliation` even resolves, proving
      opening doesn't block on the scan)
- [x] Reopen an existing collection → state matches what was persisted, no
      duplicate media identities created (same test file: same media id,
      same tag id, same mapping survive a close/reopen round trip)
- [x] Full tag/filter/navigate/edit-mapping/undo loop exercised as one
      continuous session, not just per-command unit tests
      (`test_full_tag_filter_navigate_edit_undo_loop_in_one_continuous_session`)
- [x] Launching Prismic with a `.prismic` file path argument opens straight
      to that collection — tested at the `PrismicSession`/`open_collection`
      level (`test_opening_with_a_direct_prismic_file_path_...`); full
      OS-level double-click verification is still Phase 7's job once the
      file association exists, per the original scope note here

## Responsiveness under load

- [x] Rapid navigation (`tests/gui/test_responsiveness.py`): a burst of
      key presses, deliberately overshooting past the last item, lands on
      a correct, consistent final state. Note: the viewer's image decode
      is synchronous today (see the Phase 5 file's note on why
      `ImageLoader`'s generation-staleness machinery isn't wired into the
      viewer yet), so there's no genuine async race to provoke with small
      test fixtures — what this actually guards is state corruption from a
      rapid input burst, not stale-frame flicker. Revisit with a real
      staleness test once the viewer routes through `ImageLoader`.
- [x] Rapid filter toggling leaves a consistent result set (same file)
- [x] A large collection — **2,000 files** chosen as the stress number
      (`tests/integration/test_large_collection.py`): large enough to
      meaningfully exercise scan/hash/reconcile and the query layer's sort
      at a scale well past casual manual testing, small enough to stay a
      normal (not skipped-for-being-slow) part of the suite. Confirms
      `PrismicSession.open()` itself returns in well under a second
      regardless of collection size (it only *schedules* the background
      scan, per Phase 3's `WorkerPool`) and that a same-content rescan
      stays fast (all-unchanged, no per-file DB writes).

## Failure handling

- [x] Failed collection open (corrupt `.prismic`, incompatible/too-new
      schema) surfaces a clear error and leaves no partial session,
      verified via the real `MainWindow` — not just the Phase 1 unit tests
      for the same error types (`tests/gui/test_failure_handling.py`)
- [x] Collection locking actually prevents a second Prismic instance from
      opening the same collection for writing — verified with a genuinely
      separate OS process (`subprocess.Popen`, not just a second object in
      the same process), in `tests/integration/test_locking.py`
- [x] Mid-scan filesystem errors don't crash the app or corrupt state: a
      file disappearing between the scanner listing it and the hasher
      reading it (`tests/integration/test_mid_scan_failures.py`) — the
      other file in the same scan is still correctly recorded
- [x] Opening/double-clicking a `.prismic` file already open elsewhere is
      handled gracefully: a clear `QMessageBox` naming the exact locked
      path, verified both automatically and live via computer-use with two
      real running instances (see below)

## Full computer-use verification pass

Walked every primary workflow live, using a scratch folder with a real
image and a real audio-bearing WebM (not the "my data folder" used in
Phase 5, so this pass would cover video specifically): open collection,
create/apply/remove/delete tags (both the `t`+digit chord *and* clicking
the per-item checkbox directly — Phase 5 only tried the chord), filter,
navigate, view an image, **play a video** (confirmed actual frame
rendering via a zoomed screenshot mid-playback, not just "no error"), and
the two-instance locked-open case.

- [x] Every workflow above confirmed against the real running app
- [x] UX rough edges found and fixed, not just noted:

**Bug 1 — `open_collection()` crashed unhelpfully on a plain string path.**
Writing the two-instance locking test (a subprocess script handed a path
via `sys.argv`, naturally a `str`) hit `AttributeError: 'str' object has
no attribute 'is_file'` instead of a domain error. `persistence/collection.py::open_collection`
now accepts `str | os.PathLike[str]` and converts internally — a small,
low-risk hardening exactly in this phase's spirit, since real callers
(bootstrap.py, subprocess scripts, anything else that hands in a path)
shouldn't have to know this function was written assuming a `Path`
specifically.

**Bug 2 — the "already open elsewhere" dialog could appear before the
window itself was ever shown.** `MainWindow.__init__` opened
`initial_path` synchronously, but the caller (`bootstrap.run()`) doesn't
call `.show()` until *after* construction returns. Launching a second
instance against an already-open collection therefore showed a
`QMessageBox` floating with no visible parent window, and only *after*
dismissing it did an empty "No collection open" window suddenly appear —
confusing, even though the underlying error handling was already correct.
Fixed by deferring the initial-path open with `QTimer.singleShot(0, ...)`,
so it runs after the event loop starts (and `.show()` has taken effect)
instead of during construction. Verified live: the window (with its menu
bar) is now visibly there first, and the dialog reads naturally as "this
window couldn't open X." Two new regression tests in
`tests/gui/test_main_window.py` assert the open is genuinely deferred
(`session is None` immediately after construction, only becoming non-None
after pumping the event loop).

## Addendum: focus-forwarding instead of an error (post-phase, user-requested)

After this phase shipped, the user hit the locked-collection dialog by
launching a second instance against a collection they already had open,
and asked for better behavior — specifically, whether opening the same
collection twice could just work. It deliberately still can't (the
single-writer-per-collection rule is load-bearing: see overview section 6
and the reasoning in Phase 1), but the user picked a middle path over
AskUserQuestion: **the second launch now focuses the already-open window
instead of erroring**, rather than either allowing real concurrent access
or just prettifying the error text.

`ui/instance_bridge.py` adds a `QLocalServer`/`QLocalSocket`-based IPC
channel, keyed by a hash of the collection's database path, layered
*on top of* the Phase 1 file lock (which stays authoritative — the socket
is a best-effort nicety, not a second source of truth). When
`MainWindow.open_collection()` hits `CollectionLockedError`, it now tries
`request_focus()` first; only if that fails (no live listener reachable)
does it fall back to the `QMessageBox`. A CLI/double-click launch
(`is_startup=True`) that successfully focuses another instance just closes
itself instead of leaving an empty window behind.

**Real finding from live verification, not just theorized:** asking the
existing window to `activateWindow()` from a background process can be
silently denied by Windows' own focus-stealing prevention — the same
mechanism already documented above this section for this app's own launch
sequence. `QApplication.alert(self)` (the OS-sanctioned "ask for
attention" request — taskbar flash on Windows, dock bounce on macOS) is
added as a fallback that works even when full activation is denied.

Verified live end-to-end: launching a second instance against an
already-open collection with the fix in place left **no** duplicate
window and **no** error dialog — only the original instance remained
running. Four new tests in `tests/gui/test_instance_bridge.py` cover the
signal delivery and both the manual-open and startup-launch cases.

## Tests

- [x] `tests/integration/test_end_to_end.py`, `test_large_collection.py`,
      `test_locking.py`, `test_mid_scan_failures.py`; `tests/gui/test_failure_handling.py`,
      `test_responsiveness.py`, `test_instance_bridge.py`; plus two new
      regression tests in `tests/gui/test_main_window.py` for the
      deferred-open fix
- [x] What's realistically only verifiable by hand, documented rather than
      silently skipped: true OS-level double-click launch (needs Phase 7's
      file association); real perceived responsiveness/frame timing on an
      actual display, as opposed to state-correctness under rapid
      synthetic input (which *is* automated, per above)
