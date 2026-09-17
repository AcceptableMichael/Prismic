# Phase 1 — Domain & persistence

Goal: the durable data model exists, is correct under transactions and
migrations, and nothing above this layer needs to know that SQLite is
underneath it. Corresponds to overview sections 2, 3 (identity fields only —
reconciliation logic itself is Phase 2), and 6 — with the collection-file
shape amended per
[`requirements-amendments.md`](../requirements-amendments.md) (single
`.prismic` file, not a `.prismic/` directory).

## Domain types (`domain/`)

- [x] `Media` value/entity type: `id`, `relative_path`, `content_hash`,
      `size`, `mtime`, `state`
- [x] `Tag` type: immutable `id`, mutable `name`, with the validation rules
      from the overview (non-empty after trim, unique, case-sensitive,
      Unicode allowed, no newlines)
- [x] `Collection` type representing an opened collection root
- [x] Keep these free of Qt and SQLite imports — domain layer has no
      infrastructure dependencies

## Database schema (`persistence/database.py`, `persistence/migrations.py`)

- [x] `media`, `tags`, `media_tags` tables per the minimum logical schema in
      the overview
- [x] Foreign keys enabled and enforced
- [x] Unique constraint on tag names
- [x] Unique constraint on `(media_id, tag_id)` mappings
- [x] Indexes supporting both media→tags and tags→media queries
- [x] Versioned, transactional migration mechanism (schema version tracked
      in the DB itself, via `PRAGMA user_version`)
- [x] A failed migration leaves the previous valid schema intact — verified
      with a test that induces a mid-migration failure
- [x] Never silently replace an unreadable/incompatible database with a new
      empty one — detect and surface this as an error instead
      (`IncompatibleDatabaseError`)

## Collection lifecycle (single-file `.prismic` artifact)

Per [`requirements-amendments.md`](../requirements-amendments.md), the
collection's persistent data is a single SQLite file named `<name>.prismic`
living directly in the collection root — not a hidden `.prismic/` directory.
This supersedes overview section 2's directory-based description.

- [x] SQLite opened in a rollback-journal mode (`DELETE`/`TRUNCATE`), not
      WAL, so that with no connection open the collection is genuinely one
      file on disk — verified no lingering `-wal`/`-shm` files after a clean
      close
- [x] Opening a collection accepts either a directory (locate its single
      `*.prismic` file) or a direct file path (the OS file-association
      launch case from Phase 7 hands this in via argv) — both converge on
      one code path (`persistence/collection.py::open_collection`)
- [x] Creating a new collection in a directory with no `.prismic` file yet:
      derive/prompt for a filename, create it there (derives `<dirname>.prismic`;
      an actual filename *prompt* is a UI concern for Phase 5)
- [x] Finding more than one `*.prismic` file at a directory root is
      surfaced as an error, not silently resolved by picking one
- [x] Full open sequence: resolve the `.prismic` file → open or create it →
      validate/migrate its schema → construct the session object →
      (reconciliation itself is wired in Phase 2, but the hook point exists
      here — `OpenCollection.connection` is what Phase 2's reconciler will use)
- [x] A failed open or migration leaves no partially-active session
- [x] The collection's own `.prismic` file is excluded from media discovery
      by exact match (`Collection.is_collection_file`; the scanner that
      calls it is Phase 2)
- [x] Global application preferences stored separately from collection data
      (`persistence/preferences.py`: platform config dir — `%APPDATA%/Prismic`
      on Windows, `~/Library/Application Support/Prismic` on macOS,
      `$XDG_CONFIG_HOME/prismic` or `~/.config/prismic` on Linux)
- [x] Collection locking so only one Prismic instance writes to a given
      `.prismic` file at a time (`persistence/lockfile.py`: an OS-level
      advisory lock on the database file itself, tied to an open file
      descriptor's lifetime — never a separate sidecar lock file, so it
      can't go stale)

## Repositories (`persistence/repositories/`)

- [x] Media repository: create/read/update by id, lookup by relative path,
      lookup by content hash, list all
- [x] Tag repository: CRUD, uniqueness enforcement surfaced as a domain-level
      error (not a raw SQLite exception leaking upward)
- [x] Mapping repository: add/remove media↔tag links, query tags for a
      media item and media for a set of tags
- [x] Each repository owns its SQLite connection/cursor usage per the
      concurrency rules in section 7 (no indiscriminate cross-thread sharing)
      — cross-thread ownership itself is Phase 3's worker-pool concern; these
      repositories just take the connection they're given and don't stash
      global state

## Tests (`tests/unit`, `tests/integration`)

- [x] Schema creation from empty
- [x] Migration from each prior schema version to latest (only one migration
      exists so far — version 0 → 1; the mechanism is exercised more
      thoroughly by the induced-failure test below)
- [x] Constraint violations rejected (duplicate tag name, duplicate mapping,
      orphaned foreign key)
- [x] Transaction rollback leaves no partial writes
- [x] Failed migration recovery leaves the old schema usable
- [x] Collection open/create round-trip, including the failed-open-leaves-no-
      session case

## Notable bug caught during implementation

Windows byte-range locks (`msvcrt.locking`) are **mandatory**, not advisory
— unlike POSIX `flock`. The collection lock originally locked byte 0 of the
`.prismic` file, which blocked SQLite's own separate file handle from
reading the header at all (`disk I/O error`). Fixed by locking a byte range
far past any real file content instead (mirroring SQLite's own internal
`PENDING_BYTE` trick) — but the first offset tried, `1 << 30`, turned out to
be SQLite's actual `PENDING_BYTE`, causing `database is locked` instead.
Landed on `1 << 40`, well clear of SQLite's own reserved lock bytes. See
[`lockfile.py`](../../../src/prismic/persistence/lockfile.py) for the
mechanism and tests in `tests/unit/persistence/test_lockfile.py` and
`tests/integration/test_collection_lifecycle.py` for cross-instance locking
behavior.
