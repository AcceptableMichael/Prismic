# Phase 2 — Indexing & reconciliation

Goal: the filesystem and the database agree on what media exists and where,
including across moves and edits, without ever guessing when it isn't safe
to. Corresponds to overview section 3 and the reconciliation parts of
section 7.

## Filesystem scanner (`indexing/scanner.py`)

- [x] Recursively walks the collection root
- [x] Does not follow symbolic links
- [x] Does not follow Windows junctions/reparse points
- [x] Excludes the collection's own `.prismic` file (by exact path match via
      `Collection.is_collection_file`, not just incidentally via extension
      filtering)
- [x] Continues past individual permission/I/O failures on a per-file basis
      rather than aborting the whole scan
- [x] A failed/partial scan is never interpreted as "these files were
      deleted" — the scanner just yields fewer files; only the reconciler
      acts on scan results, and it only ever sees what a scan *did* find
- [x] Classifies candidate files by extension against a supported-format
      list (`media/formats.py` — a placeholder pending Phase 4's real
      decode-validated definition; extension is only a candidate filter,
      never proof of validity)

## Hashing (`indexing/hashing.py`)

- [x] Content hashing function (BLAKE2b, chunked reads) used consistently
      for identity comparisons
- [x] Pure stdlib function with no Qt/GUI dependency — safe to call from any
      thread. The actual background-thread *dispatch* is Phase 3's job: the
      architecture overview places "worker pool" under `PrismicSession`
      assembly (see `phases/03-application-layer.md`), which doesn't exist
      yet. This phase provides the thread-safe building blocks; Phase 3
      wires them onto an actual QThread/executor.

## Reconciler (`indexing/reconciler.py`)

- [x] New file → new media identity
- [x] Unchanged file (path + hash match) → no-op
- [x] Changed content at an existing path → old identity becomes missing,
      replacement gets a new identity; tags are not transferred (there's
      nothing to transfer them *to* yet — Phase 3 owns mapping commands)
- [x] Unique move (missing record's hash matches exactly one new file) →
      relink existing identity to new path
- [x] Ambiguous move (hash matches multiple new files) → do not guess; old
      identity stays unresolved, all candidates stay distinct
- [x] Missing file (recorded but not found this scan) → marked missing, not
      deleted
- [x] Unsupported file (extension not in the candidate set) → ignored, not
      recorded as missing media (the scanner never surfaces it in the first
      place)
- [x] Unreadable file (permission/I/O error) → skipped without corrupting
      state for other files (its existing record, if any, is left
      completely untouched for that pass — not marked missing just because
      it couldn't be re-verified)
- [x] Hard-link relationships are not modeled — each path is treated as an
      independent candidate regardless of inode sharing; no special-casing
      added
- [x] Prismic never modifies, moves, renames, or deletes user media files
      (nothing in the reconciler touches the filesystem at all — it only
      reads it via the scanner and writes to the database)

**Design note on move ambiguity:** the overview's wording ("a missing
record's hash matches exactly one new file") reads naturally as *per missing
record*. The implementation holds both sides to the same standard: a relink
only happens when exactly one candidate (an already-missing record, or a
previously-active record whose path wasn't observed this scan) and exactly
one unmatched scanned file share a content hash. Two candidates matching one
new file is just as unsafe to guess at as one candidate matching two new
files, so both are treated as ambiguous.

## Background execution & staleness (overview section 7)

- [x] Every scan/hash operation carries a generation/request id
      (`Reconciler.begin_scan()` / `reconcile(generation, ...)`)
- [x] Stale scan results are discarded before they can mutate current state
      — a `reconcile()` call for a generation that's no longer current is a
      no-op (`ReconciliationResult(applied=False)`), verified with a test
      that starts a second scan before "finishing" the first
- [ ] Scans and hashing run off the GUI thread; GUI stays usable throughout
      — not yet meaningful to check off: there's no GUI event loop driving
      this yet (Phase 5), and no worker pool to dispatch onto (Phase 3).
      Everything here is written to be safely callable from a background
      thread (no Qt imports, no shared mutable state beyond the `Reconciler`
      instance itself, which a single worker will own) — actually running
      it off-thread is Phase 3/5's wiring job.
- [ ] Initial scan-and-hash on collection open runs in the background per
      the lifecycle in Phase 1 — deferred for the same reason: there's no
      worker pool yet to run it on. `indexing.reconciler.run_reconciliation`
      is the entry point Phase 3 should call from that worker.

## Tests (`tests/unit/indexing`, `tests/integration`)

- [x] New file
- [x] Unchanged file
- [x] Changed file
- [x] Unique move
- [x] Ambiguous move
- [x] Missing file
- [x] Unsupported file
- [x] Unreadable file
- [x] Symlink/junction exclusion (both a POSIX symlink and, on Windows, a
      real NTFS junction created via `mklink /J`, which doesn't require
      elevated privileges)
- [x] Stale scan result correctly discarded
