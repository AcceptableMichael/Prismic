# Requirements amendments

Requirements given verbally/in-chat that supplement
[`initial technical overview.md`](../owned%20by%20human/initial%20technical%20overview.md)
and [`intended use.md`](../owned%20by%20human/intended%20use.md) but haven't
been folded into those files. Claude can't edit anything under
`owned by human/` per `CLAUDE.md`, so amendments live here until the human
merges them into the source docs (or decides not to). Check here alongside
the human-owned overview when the two might disagree.

## 2026-09-16: single-file, double-click-openable collection artifact

**Status: merged into `initial technical overview.md` section 2 (and the
`.prismic` exclusion bullet in section 3) on 2026-09-16, at the human's
explicit request to edit the human-owned doc this once.** Left in place
below as the design rationale — the overview itself doesn't carry the "why."

**What was asked:** the artifact/database Prismic produces for a collection
should be a single file, sitting in the root directory being tracked, that
self-contains all of Prismic's data for that collection, and that opens
Prismic to that directory when double-clicked/executed.

**Assessment:** makes sense, with one mechanism clarification, spelled out
below. This supersedes the `.prismic/`-directory design described in
overview section 2.

### Decisions

- **Format:** a single SQLite database file, extension `.prismic`, living
  directly in the collection root (e.g. `<root>/<name>.prismic`) — not a
  hidden `.prismic/` directory.
- **Journal mode:** rollback journal (`DELETE`/`TRUNCATE`), not WAL. WAL
  leaves permanent `-wal`/`-shm` sidecar files next to the database, which
  would break the "single file at rest" property. A `-journal` file may
  appear transiently mid-transaction; that's normal SQLite behavior and
  disappears on commit, not something to work around.
- **"Double-click to open" mechanism:** an OS-level file-type association,
  registered by the installer/bundle, mapping `.prismic` → the Prismic
  executable (equivalent to how `.blend`, `.psd`, `.aep`, etc. work). The OS
  invokes `prismic <path-to-file>` on double-click; a data file cannot
  itself be a cross-platform executable without embedding a full runtime
  per collection, which would contradict "self-contained data" in spirit
  and be impractical to maintain/update.
- **One collection file per directory:** exactly one `*.prismic` file is
  expected at a given root. Finding more than one there is an error
  surfaced to the user, not a silent pick-one. Nested collections (a
  `.prismic` file inside a subdirectory of another collection) are out of
  scope for v1 — don't auto-discover them.
- **Opening path:** the application-layer "open collection" entry point
  accepts either a directory (find its `*.prismic` file) or a direct file
  path (from argv, i.e. the OS association launch) — both converge on the
  same code path.

### Plans updated as a result

- [`phases/01-domain-and-persistence.md`](phases/01-domain-and-persistence.md) —
  collection lifecycle rewritten around the single `.prismic` file.
- [`phases/05-ui-and-viewer.md`](phases/05-ui-and-viewer.md) — app accepts a
  file-path launch argument and opens straight to that collection.
- [`phases/06-integration-and-hardening.md`](phases/06-integration-and-hardening.md) —
  end-to-end double-click-open test, and "already open elsewhere" handling.
- [`phases/07-distribution.md`](phases/07-distribution.md) — register the
  `.prismic` file association per platform as part of packaging.

### Resolved

Folded into `initial technical overview.md` directly (see Status above),
using `.prismic` as the extension.
