# Roadmap

This is the top-level plan for building Prismic out of the requirements and
architecture in
[`initial technical overview.md`](../owned%20by%20human/initial%20technical%20overview.md).
Per [`development flow.md`](../owned%20by%20human/development%20flow.md), work
down this list top to bottom, check items off as they land, and edit these
plans freely as understanding improves — they're owned by Claude, not fixed
in stone.

Each phase has its own file in [`phases/`](phases/) with detailed sub-goals
and checkboxes. This file tracks phase-level status only; check a phase's box
here once *all* of its sub-goals are checked off in its own file.

The phase order follows the dependency direction from the architecture doc
(`UI -> Application -> Domain/interfaces -> Infrastructure`), built bottom-up
so each layer has something real underneath it to integrate against, with UI
arriving once there's application-layer behavior worth showing.

## Phases

- [x] **Phase 0 — [Foundations](phases/00-foundations.md)**
      Toolchain, project skeleton, CI-free local dev loop, and the
      computer-use verification workflow. Mostly done already; this file
      mainly records what's in place and what's still owed.
- [x] **Phase 1 — [Domain & persistence](phases/01-domain-and-persistence.md)**
      Media/Tag/Collection domain types, SQLite schema, migrations,
      repositories, and the single-file `.prismic` collection lifecycle
      (see [`requirements-amendments.md`](requirements-amendments.md)).
- [ ] **Phase 2 — [Indexing & reconciliation](phases/02-indexing-and-reconciliation.md)**
      Filesystem scanning, content hashing, and move/change/missing
      reconciliation against persisted media identity.
- [ ] **Phase 3 — [Application layer](phases/03-application-layer.md)**
      `PrismicSession`, the command dispatcher, tag/mapping/filter commands,
      undo history, and the query layer (intersection filtering, ordering,
      selection invariants).
- [ ] **Phase 4 — [Media layer](phases/04-media-layer.md)**
      Supported-format definition, image/video loading, bounded caching,
      downsampling, and stale-result suppression, backed by test fixtures.
- [ ] **Phase 5 — [UI & viewer](phases/05-ui-and-viewer.md)**
      Real main window wired to the application layer: tag list, filter
      selection, result view, media viewer (zoom/pan/playback), and the
      keyboard input layer with chorded shortcuts.
- [ ] **Phase 6 — [Integration & hardening](phases/06-integration-and-hardening.md)**
      End-to-end open-collection flow, responsiveness under rapid
      navigation/changing result sets, failure handling, collection locking,
      and a full computer-use pass over the primary workflows.
- [ ] **Phase 7 — [Distribution](phases/07-distribution.md)**
      Self-contained packaging for Windows/macOS/Linux and platform-specific
      verification of media playback and filesystem behavior.

## Cross-cutting, ongoing for every phase

These aren't a phase of their own — they apply throughout, per
[`testing flow.md`](../owned%20by%20human/testing%20flow.md) and
[`project guidance.md`](project%20guidance.md):

- Add/extend pytest-qt and unit tests alongside the code they cover, not as
  an afterthought.
- Run `ruff check`, `ruff format`, `mypy` (strict) before considering a unit
  of work done.
- For anything UI-visible, verify with computer-use (see the launch-path note
  in `project guidance.md`) in addition to automated tests.
- Commit at each meaningful checkpoint with real messages.
- Update this roadmap and the relevant phase file as scope shifts — don't let
  them drift from what's actually true.
