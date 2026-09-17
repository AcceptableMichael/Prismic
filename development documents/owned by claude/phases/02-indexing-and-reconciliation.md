# Phase 2 — Indexing & reconciliation

Goal: the filesystem and the database agree on what media exists and where,
including across moves and edits, without ever guessing when it isn't safe
to. Corresponds to overview section 3 and the reconciliation parts of
section 7.

## Filesystem scanner (`indexing/scanner.py`)

- [ ] Recursively walks the collection root
- [ ] Does not follow symbolic links
- [ ] Does not follow Windows junctions/reparse points
- [ ] Excludes `.prismic/`
- [ ] Continues past individual permission/I/O failures on a per-file basis
      rather than aborting the whole scan
- [ ] A failed/partial scan is never interpreted as "these files were
      deleted"
- [ ] Classifies candidate files by extension against the Phase 4
      supported-format list (extension is only a candidate filter — actual
      decode validity is Phase 4's job)

## Hashing (`indexing/hashing.py`)

- [ ] Content hashing function used consistently for identity comparisons
- [ ] Runs in a background worker, not on the GUI thread

## Reconciler (`indexing/reconciler.py`)

- [ ] New file → new media identity
- [ ] Unchanged file (path + hash match) → no-op
- [ ] Changed content at an existing path → old identity becomes
      missing/history state, replacement gets a new identity; tags are not
      transferred
- [ ] Unique move (missing record's hash matches exactly one new file) →
      relink existing identity to new path
- [ ] Ambiguous move (hash matches multiple new files) → do not guess; old
      identity stays unresolved, all candidates stay distinct
- [ ] Missing file (recorded but not found this scan) → marked missing, not
      deleted
- [ ] Unsupported file (extension not in the candidate set) → ignored, not
      recorded as missing media
- [ ] Unreadable file (permission/I/O error) → skipped without corrupting
      state for other files
- [ ] Hard-link relationships are not modeled — don't try to special-case
      them
- [ ] Prismic never modifies, moves, renames, or deletes user media files

## Background execution & staleness (overview section 7)

- [ ] Scans and hashing run off the GUI thread; GUI stays usable throughout
- [ ] Every scan/hash operation carries a generation/request id
- [ ] Stale scan results are discarded before they can mutate current state
      (e.g. a new scan started while an old one is in flight)
- [ ] Initial scan-and-hash on collection open runs in the background per
      the lifecycle in Phase 1

## Tests (`tests/integration`)

- [ ] New file
- [ ] Unchanged file
- [ ] Changed file
- [ ] Unique move
- [ ] Ambiguous move
- [ ] Missing file
- [ ] Unsupported file
- [ ] Unreadable file
- [ ] Symlink/junction exclusion
- [ ] Stale scan result correctly discarded
