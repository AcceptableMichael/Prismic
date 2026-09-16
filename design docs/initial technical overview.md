# Prismic — Feature Requirements

### 1. Purpose

Prismic is a cross-platform desktop application for viewing and organizing a collection of image and video files using user-defined tags.

### 2. Media viewing

* Display common image formats.
* Support video playback, with **WebM required** at minimum.
* Provide normal image-viewer interactions, including:

  * zooming
  * scrolling/panning
  * double-click interaction for zoom
  * other conventional viewer interactions as appropriate
* Provide normal video-player interactions, including:

  * play/pause
  * seeking
  * navigation through the media
* The viewer should feel responsive during interaction.

### 3. File collection

* Prismic operates on the files contained within a user-selected directory, and all directories within it.
* Files in that directory can be associated with zero or more user-defined tags.
* The application's persistent data should normally be stored directly within the corresponding media directory.
* The application should maintain enough information to identify a previously mapped file if it is subsequently moved away from its stored path.
* File contents should therefore be hashed and the hash stored as part of the file's identity information.

### 4. Tags

* Users can create tags.
* Users can delete tags.
* Users can otherwise modify tags as needed for normal CRUD operation.
* Files and tags have a **many-to-many relationship**.
* Users can add/remove mappings between files and tags.
* Mapping operations must be fast and suitable for keyboard-driven workflows.

### 5. Filtering

* Users can select multiple tags to filter the collection.
* The resulting collection is the **intersection** of the files associated with all selected tags.
* The filtered result set is dynamically recalculated as tags are selected or deselected.
* The user can navigate through the resulting set with the arrow keys.
* The result set may be created and changed arbitrarily while the application is running.
* The currently displayed file can have its tag mappings edited without leaving the viewer.
* Filtering and editing should remain responsive even while the displayed result set is changing.

### 6. Keyboard-driven interaction

* Keyboard interaction is a primary part of the application UX.
* The application will support numerous keyboard shortcuts and multi-key/chord interactions.
* Keyboard operations should make common tag and mapping CRUD operations extremely fast.
* UI state should update in realtime as the user types and performs keyboard operations.
* Keyboard interaction should not require the user to repeatedly switch between mouse-oriented controls for normal workflows.

### 7. Undo

**All mutating operations must be undoable**, including:

* changes to the selected-tag/filter state
* tag creation
* tag modification
* tag deletion
* file/tag mapping creation
* file/tag mapping deletion
* other CRUD operations introduced by the application

Undo must correctly restore the relevant application and persistent state.

### 8. Cross-platform / distribution

* Prismic should run on Windows, macOS, and Linux.
* The application should not require the user to separately install Python or other dependencies.
* The eventual distribution should aim to provide a self-contained executable/application bundle.
* Python itself is an acceptable implementation language.

---

# Architectural Overview

**Verdict: ready for development handoff.**

The remaining ambiguity has been resolved below as explicit v1 semantics rather than left as a decision list for the implementation agent. These choices are deliberately conservative and can be changed later without requiring a different overall architecture.

## 1. Core architecture

```text
                    ┌───────────────────────┐
                    │       Qt UI           │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │ Application Layer     │
                    │ State / Commands      │
                    │ Queries / Undo / Input │
                    └───────┬───────┬───────┘
                            │       │
                ┌───────────▼─┐   ┌─▼────────────────┐
                │ Persistence │   │ Media Services   │
                │ SQLite      │   │ Decode / Cache   │
                └───────────┘   └─────────┬─────────┘
                                          │
                                    ┌─────▼─────┐
                                    │Filesystem │
                                    └───────────┘
```

The central invariant is:

> **Every user-visible mutation passes through the application command layer.**

UI components do not directly implement persistence or undo.

The application owns one `PrismicSession` for the currently open collection:

```text
PrismicSession
├── collection root
├── database
├── repositories
├── application state
├── command dispatcher
├── undo history
├── filesystem reconciler
├── media services
└── worker pool
```

Only one collection is active at a time.

---

## 2. Collection and persistence semantics

The selected directory is the collection root.

Prismic stores its metadata in:

```text
<collection>/.prismic/
```

`.prismic` is owned by Prismic, is excluded from media discovery, and travels with the collection when the directory is moved or copied.

Media paths are stored relative to the collection root.

The database is authoritative for Prismic metadata. Global application preferences are stored separately from collection data.

Opening a collection:

1. establishes the root;
2. opens or creates `.prismic`;
3. validates/migrates the database;
4. establishes the session;
5. starts filesystem reconciliation.

A failed open or migration leaves no partially active session.

Initial scanning and hashing occur in background workers; the GUI remains usable throughout.

---

## 3. Media identity and reconciliation

Each media record has:

```text
id
relative_path
content_hash
size
mtime
state
```

`id` is the stable logical identity used by tag mappings.

`content_hash` is content evidence, not the database identity.

`relative_path` is the current observed location.

### Move detection

If a missing media record's content hash matches exactly one newly discovered file, the existing media identity is relinked to the new path.

If there is no match, the new file receives a new identity.

If multiple candidates match, Prismic does not guess; the old identity remains unresolved and the candidates remain distinct.

### Content replacement

If a file at an existing path has different content from its recorded hash, the old identity becomes missing/history state and the replacement receives a new media identity.

Tags are **not** silently transferred to changed content.

### Filesystem traversal

V1:

* recursively follows ordinary directories;
* does not follow symbolic links;
* does not follow Windows junctions/reparse points;
* excludes `.prismic`;
* continues past individual permission/I/O failures.

A failed scan is not interpreted as deletion.

Hard-link relationships are not modeled.

Prismic does not modify, move, rename, or delete user media files in v1.

---

## 4. Tags and filtering

Tags have:

```text
id       immutable
name     mutable
```

Tag names:

* must be non-empty after trimming;
* are unique;
* are case-sensitive;
* may contain Unicode;
* may not contain newlines.

Mappings use IDs, never names.

Filtering is relational and represents the intersection of all selected tags.

With no selected tags, all discovered supported media are eligible.

Result ordering is deterministic:

```text
normalized relative path, ascending
```

The current item must always be either:

```text
null
```

or an item in the active result set.

If the current item leaves the result set, selection moves deterministically to the nearest surviving item in the previous navigation order; if none survives, the first result is selected; if there are no results, the current item becomes null.

---

## 5. Undo

Undo is session-local.

Restarting Prismic clears undo history.

Every persistent or filter-state mutation is represented by a logical command and is undoable.

Undo operates on logical user actions rather than low-level events. For example, a completed tag rename is one undoable action, not one action per keystroke.

Database snapshots are not used for undo.

Redo is not part of v1.

External filesystem changes are observed and reconciled, but are not undoable because Prismic did not perform them.

Every persistent command follows:

```text
validate
  ↓
begin transaction
  ↓
mutate database
  ↓
commit
  ↓
publish new application state
```

A failed transaction publishes no partial state.

---

## 6. Database

SQLite is the persistence layer.

Minimum logical schema:

```text
media
─────
id
content_hash
relative_path
size
mtime
state

tags
────
id
name

media_tags
──────────
media_id
tag_id
PRIMARY KEY(media_id, tag_id)
```

Required constraints/indexes include:

* foreign keys enabled;
* unique tag names;
* unique media/tag mappings;
* indexes supporting both media→tags and tags→media queries.

Schema changes use versioned, transactional migrations.

A failed migration must leave the previous valid schema intact. The application must never silently replace an unreadable/incompatible database with a new empty database.

Only one Prismic instance may write to a collection at once; collection locking should enforce this where practical.

---

## 7. Background work and concurrency

The GUI thread owns presentation and application-visible state.

Background workers perform:

* filesystem traversal;
* hashing;
* media decoding;
* preload/cache work;
* other potentially blocking I/O.

SQLite connections are explicitly owned by their respective execution contexts rather than shared indiscriminately across threads.

All asynchronous operations carry a generation/request identity.

Stale results must be discarded before they can modify current state.

This applies to:

```text
filesystem scans
hash operations
image decoding
video/media loading
preloading
```

Cancellation may be used for efficiency, but stale-result suppression is the correctness mechanism.

---

## 8. Media support

The initial implementation must define and test a concrete supported-format set rather than treating every extension as playable.

Image formats should include the conventional Qt-supported formats selected by the implementation.

Video playback must support WebM with at least the codecs actually provided by the chosen playback stack and validated by representative fixtures.

Audio accompanying supported video is played when present.

The implementation must include test fixtures for:

```text
supported image
large image
corrupt image
supported WebM
audio-bearing WebM
unsupported media
```

Animated image formats are treated according to the capabilities explicitly enabled by the chosen Qt media/image stack; v1 does not promise animation semantics beyond those tested fixtures.

File extensions are only candidate classification. Actual decoding determines validity.

---

## 9. Viewer and memory behavior

The viewer must remain responsive during navigation and interaction.

Large images must not be retained indefinitely at full decoded resolution.

The media layer therefore uses:

* bounded caching;
* background decoding;
* appropriate downsampling;
* release/eviction of obsolete decoded data.

Rapid navigation must not allow an older decode to replace the currently displayed media.

---

## 10. Keyboard architecture

Keyboard interaction is handled by an application-level input layer rather than being scattered across widgets.

Resolution precedence is:

```text
text-editing context
    ↓
local/modal interaction
    ↓
viewer interaction
    ↓
global application command
```

Chorded shortcuts have explicit cancellation/timeout behavior.

Normal tag and mapping workflows must be achievable without repeatedly moving focus to mouse-oriented controls.

---

## 11. Qt/UI architecture

Use Qt model/view abstractions for potentially large tag and result collections.

The UI is responsible for presentation and input.

The application layer is responsible for:

```text
state
commands
queries
filter semantics
selection semantics
undo
```

The persistence layer is responsible for durable storage.

The indexing layer is responsible for filesystem observation/reconciliation.

The media layer is responsible for loading and caching media.

No widget owns product-level persistence semantics.

---

## 12. Repository layout

```text
prismic/
├── pyproject.toml
├── README.md
├── LICENSE
│
├── src/
│   └── prismic/
│       ├── __main__.py
│       ├── bootstrap.py
│       │
│       ├── application/
│       │   ├── session.py
│       │   ├── state.py
│       │   ├── commands/
│       │   ├── queries/
│       │   ├── history.py
│       │   └── input/
│       │
│       ├── domain/
│       │   ├── media.py
│       │   ├── tag.py
│       │   └── collection.py
│       │
│       ├── persistence/
│       │   ├── database.py
│       │   ├── migrations.py
│       │   └── repositories/
│       │
│       ├── indexing/
│       │   ├── scanner.py
│       │   ├── reconciler.py
│       │   └── hashing.py
│       │
│       ├── media/
│       │   ├── loader.py
│       │   ├── image.py
│       │   ├── video.py
│       │   └── cache.py
│       │
│       └── ui/
│           ├── main_window.py
│           ├── viewer.py
│           ├── tag_model.py
│           └── filter_model.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── gui/
│   └── fixtures/
│
└── tools/
```

The exact filenames may change; the dependency boundaries must not.

Dependency direction:

```text
UI
 ↓
Application
 ↓
Domain / interfaces
 ↓
Infrastructure
```

Qt, SQLite, and the filesystem are mechanisms, not owners of product semantics.

---

## 13. Testing and acceptance gates

Tests must cover at least:

### Persistence

```text
schema creation
migration
constraints
transaction rollback
failed migration recovery
```

### Commands

```text
tag creation
tag rename
tag deletion
mapping creation/deletion
filter selection/deselection
undo
multiple undo
```

### Reconciliation

```text
new file
unchanged file
changed file
unique move
ambiguous move
missing file
unsupported file
unreadable file
symlink/junction exclusion
stale scan result
```

### Queries

```text
zero tags
one tag
multiple tags
empty intersection
deterministic ordering
large result set
```

### Media

```text
supported image
large image
corrupt image
supported WebM
audio-bearing video
unsupported media
rapid navigation
stale load suppression
```

### Core invariants

```text
execute(command) → valid state

execute(command)
→ undo
→ original state
```

```text
every mapping references an existing media and tag
```

```text
current_media == null
OR
current_media ∈ active_result_set
```

```text
failed persistence
→ no published partial mutation
```

---

## 14. Distribution

Python is an implementation language, but Python is not a runtime dependency for users.

The release process must produce self-contained Windows, macOS, and Linux application distributions using an appropriate packaging/bundling mechanism.

Platform-specific media playback and filesystem behavior must be tested on each supported platform rather than assumed equivalent.
