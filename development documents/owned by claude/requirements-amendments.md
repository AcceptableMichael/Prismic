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

## 2026-09-20: three verification gates, in order

**Status: merged into `testing flow.md` (a new "When to run them"
section) on 2026-09-20, at the human's explicit request to edit the
human-owned doc this once.** Recorded here for the same reason as the
entry above — the grant was a one-off, so the standing rule in
`CLAUDE.md` (never create, edit, move, or delete anything under
`owned by human/`) is unchanged and still applies to every future
session.

**What was asked:** verification happens in this order — targeted
`pytest` for what was built, then computer use, then the full `pytest`
suite — and all three must be done before a task is considered
complete. The motivating problem was the full suite taking minutes,
which makes running it on every iteration mostly waiting.

**Why the ordering is the useful part.** The first framing of this
amendment only said "full suite at the end, targeted runs are an
escape hatch." That was weaker in two ways the human's version fixes:
it left targeted tests optional rather than required, and it never said
where computer use sits relative to either test run. Ordering them puts
the cheapest feedback first and the slowest sweep last, and stops a
manual pass being spent on code that targeted tests would already have
failed.

**One clarification written into the doc:** these are gates, not a
one-way pipeline. A bug found at gate 2 or 3 sends you back through
gate 1, with the order still holding on the way back out — otherwise
the rule reads as "one pass each" and quietly discourages re-running
the cheap checks after a late fix.

`ruff` and `mypy` are deliberately *not* gates. They're fast, and they
catch a different class of problem (a rename that missed a call site,
an unused import) that is much cheaper to find immediately than at any
gate, so they run throughout.

### Plans updated as a result

- [`project guidance.md`](project%20guidance.md) — the "Working
  independently" loop (steps 2-4) now states the three gates and their
  ordering, so the implement/verify loop doesn't reintroduce
  per-iteration full-suite runs or leave computer use unplaced.
- [`roadmap.md`](roadmap.md) — the cross-cutting testing bullets now
  distinguish the always-on static checks from the three gates, and no
  longer imply computer use is only for UI-visible changes.
