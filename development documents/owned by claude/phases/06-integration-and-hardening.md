# Phase 6 — Integration & hardening

Goal: all the layers built in Phases 1–5 work together as one coherent app
under realistic use, not just in isolation per-layer. This is where the
acceptance gates in overview section 13 get checked end-to-end rather than
per-component.

## End-to-end flows

- [ ] Fresh directory → open as collection → initial scan/hash completes in
      the background → tags and media appear correctly, GUI usable
      throughout
- [ ] Reopen an existing collection → state matches what was persisted, no
      duplicate media identities created
- [ ] Full tag/filter/navigate/edit-mapping/undo loop exercised as one
      continuous session, not just per-command unit tests
- [ ] Launching Prismic with a `.prismic` file path argument opens straight
      to that collection (the double-click case from
      [`requirements-amendments.md`](../requirements-amendments.md)); full
      OS-level double-click verification happens once Phase 7 registers the
      file association, but the argv-driven open path is testable now

## Responsiveness under load

- [ ] Rapid navigation (holding down arrow keys) does not cause stale media
      to flash or the UI to lag noticeably
- [ ] Changing filter selection rapidly does not cause visible glitches in
      the result view or viewer
- [ ] A large collection (enough media to be a realistic stress case — pick
      and document a number) opens and scans without freezing the GUI

## Failure handling

- [ ] Failed collection open (missing permissions, corrupt `.prismic`,
      incompatible schema) surfaces a clear error and leaves no partial
      session, verified via the real UI, not just the Phase 1 unit tests
- [ ] Collection locking actually prevents a second Prismic instance from
      opening the same collection for writing, verified by launching two
      instances
- [ ] Mid-scan filesystem errors (permission denied on a subdirectory, file
      disappearing mid-hash) don't crash the app or corrupt state
- [ ] Opening/double-clicking a `.prismic` file that's already open (locked)
      in another running instance is handled gracefully — e.g. focus the
      existing window or show a clear message — rather than corrupting the
      lock or crashing

## Full computer-use verification pass

- [ ] Walk every primary workflow from `intended use.md` / the overview
      (open collection, create/apply/remove tags, filter, navigate, view
      image, play video, undo) live via computer-use, using the
      `Start-Process -WindowStyle Normal` launch path from
      `project guidance.md`
- [ ] Record any UX rough edges found and fix them before considering this
      phase done — this phase is explicitly about closing gaps that
      per-layer tests can't see

## Tests

- [ ] Add integration-level tests (`tests/integration`) for the end-to-end
      flows above that are practical to automate
- [ ] Anything that's realistically only verifiable by hand (two-instance
      locking, real window responsiveness) is documented as such rather than
      silently skipped
