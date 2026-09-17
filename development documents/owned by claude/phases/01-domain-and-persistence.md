# Phase 1 — Domain & persistence

Goal: the durable data model exists, is correct under transactions and
migrations, and nothing above this layer needs to know that SQLite is
underneath it. Corresponds to overview sections 2, 3 (identity fields only —
reconciliation logic itself is Phase 2), and 6 — with the collection-file
shape amended per
[`requirements-amendments.md`](../requirements-amendments.md) (single
`.prismic` file, not a `.prismic/` directory).

## Domain types (`domain/`)

- [ ] `Media` value/entity type: `id`, `relative_path`, `content_hash`,
      `size`, `mtime`, `state`
- [ ] `Tag` type: immutable `id`, mutable `name`, with the validation rules
      from the overview (non-empty after trim, unique, case-sensitive,
      Unicode allowed, no newlines)
- [ ] `Collection` type representing an opened collection root
- [ ] Keep these free of Qt and SQLite imports — domain layer has no
      infrastructure dependencies

## Database schema (`persistence/database.py`, `persistence/migrations.py`)

- [ ] `media`, `tags`, `media_tags` tables per the minimum logical schema in
      the overview
- [ ] Foreign keys enabled and enforced
- [ ] Unique constraint on tag names
- [ ] Unique constraint on `(media_id, tag_id)` mappings
- [ ] Indexes supporting both media→tags and tags→media queries
- [ ] Versioned, transactional migration mechanism (schema version tracked
      in the DB itself)
- [ ] A failed migration leaves the previous valid schema intact — verify
      with a test that induces a mid-migration failure
- [ ] Never silently replace an unreadable/incompatible database with a new
      empty one — detect and surface this as an error instead

## Collection lifecycle (single-file `.prismic` artifact)

Per [`requirements-amendments.md`](../requirements-amendments.md), the
collection's persistent data is a single SQLite file named `<name>.prismic`
living directly in the collection root — not a hidden `.prismic/` directory.
This supersedes overview section 2's directory-based description.

- [ ] SQLite opened in a rollback-journal mode (`DELETE`/`TRUNCATE`), not
      WAL, so that with no connection open the collection is genuinely one
      file on disk — verify no lingering `-wal`/`-shm` files after a clean
      close
- [ ] Opening a collection accepts either a directory (locate its single
      `*.prismic` file) or a direct file path (the OS file-association
      launch case from Phase 7 hands this in via argv) — both converge on
      one code path
- [ ] Creating a new collection in a directory with no `.prismic` file yet:
      derive/prompt for a filename, create it there
- [ ] Finding more than one `*.prismic` file at a directory root is
      surfaced as an error, not silently resolved by picking one
- [ ] Full open sequence: resolve the `.prismic` file → open or create it →
      validate/migrate its schema → construct the session object →
      (reconciliation itself is wired in Phase 2, but the hook point exists
      here)
- [ ] A failed open or migration leaves no partially-active session
- [ ] The collection's own `.prismic` file is excluded from media discovery
      by exact match (the exclusion rule lives here even though the scanner
      that uses it is Phase 2)
- [ ] Global application preferences stored separately from collection data
      (decide and document the location, e.g. platform config dir) — unlike
      the collection file, this is app-wide state, not per-collection
- [ ] Collection locking so only one Prismic instance writes to a given
      `.prismic` file at a time (feeds the double-click-while-already-open
      handling in Phase 6)

## Repositories (`persistence/repositories/`)

- [ ] Media repository: create/read/update by id, lookup by relative path,
      lookup by content hash, list all
- [ ] Tag repository: CRUD, uniqueness enforcement surfaced as a domain-level
      error (not a raw SQLite exception leaking upward)
- [ ] Mapping repository: add/remove media↔tag links, query tags for a
      media item and media for a set of tags
- [ ] Each repository owns its SQLite connection/cursor usage per the
      concurrency rules in section 7 (no indiscriminate cross-thread sharing)

## Tests (`tests/unit`, `tests/integration`)

- [ ] Schema creation from empty
- [ ] Migration from each prior schema version to latest
- [ ] Constraint violations rejected (duplicate tag name, duplicate mapping,
      orphaned foreign key)
- [ ] Transaction rollback leaves no partial writes
- [ ] Failed migration recovery leaves the old schema usable
- [ ] Collection open/create round-trip, including the failed-open-leaves-no-
      session case
