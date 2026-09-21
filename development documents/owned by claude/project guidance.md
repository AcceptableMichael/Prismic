# Project guidance

Guidance for Claude Code (and other agents) working in this repository. This
file lives in `development documents/owned by claude/` — Claude's own space —
and Claude should keep it up to date as the project's workflow evolves.

## Project

Prismic is a cross-platform desktop app (Qt/PySide6, Python) for viewing and
tagging image/video collections. Full requirements and architecture are in
[`development documents/owned by human/initial technical overview.md`](../owned%20by%20human/initial%20technical%20overview.md) —
read it before making non-trivial changes. The repository layout and layer
boundaries (`ui/ -> application/ -> domain/ -> persistence|indexing|media/`)
described there are load-bearing; don't collapse them for convenience.

## Manual test data: `my data folder`

Next to this repo — i.e. a sibling of the `Prismic` folder, at
`../my data folder` relative to the repo root (on this machine:
`C:\Users\User\Desktop\my data folder`) — there is a small folder of sample
images (currently a handful of `.webp`/`.png`/`.jpg`/`.avif` files). It's the
human's manual testing ground for Prismic: a real directory to point the app
at when opening a collection, exercising the viewer, tagging, filtering, etc.
via computer-use or by hand.

- It lives **outside** the repo on purpose and must **never** become part of
  git/the repo — don't copy it in, don't move it in, don't add it as a
  submodule, and don't reference it from code or tests as if it were a
  project asset. If a fixture is needed for automated tests, add a real
  fixture under `tests/fixtures/` instead (see the Phase 4 media-layer plan).
- It will accumulate `.prismic/` metadata once a Prismic session opens it as
  a collection — that's expected and fine, it's the human's own working
  data, not something Claude needs to clean up.
- Treat its contents as opaque sample data, not something to curate, rename,
  or delete — it's for testing the app, not for Claude to organize.

## Environment: uv

This project uses [uv](https://docs.astral.sh/uv/) for the Python toolchain,
virtualenv, and dependencies. Don't use bare `pip`/`venv`/`python -m venv`.

```bash
uv sync                    # create/update .venv from pyproject.toml + uv.lock
uv run prismic              # launch the app
uv run pytest                # run the test suite
uv run pytest tests/unit     # run one suite (unit / integration / gui)
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy .                 # type-check (strict mode is on)

uv add <package>             # add a runtime dependency
uv add --dev <package>       # add a dev-only dependency
```

Always commit `uv.lock` alongside `pyproject.toml` changes.

If `uv` isn't on `PATH` in a given shell, it's installed via winget at
`%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe`; a PowerShell profile fallback
at `Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` also adds it
automatically. It should just work in any fresh shell.

## Packaging tools (Phase 7)

Installed via `winget` on this machine for building distributable
artifacts — see [`packaging/README.md`](../../packaging/README.md) for how
they're used:

- `UPX.UPX` — DLL/exe compression for the PyInstaller build. On `PATH` as
  `upx` (winget adds a shim at `%LOCALAPPDATA%\Microsoft\WinGet\Links`).
- `JRSoftware.InnoSetup` — builds the Windows installer. `ISCC.exe` (the
  command-line compiler) lands at
  `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`, not on `PATH` by
  default.

## Git

Git is installed standalone (winget, `Git.Git`) and on `PATH`. Global identity
is already configured — don't change `user.name`/`user.email`.

This applies regardless of where the work came from — the roadmap, a
computer-use exploration, or an ad hoc request typed straight into a chat
session that never touched the plan files. "Did this change the repo" is
what matters, not "was this on the list." A chat-only session that lands a
verified change and doesn't commit it has left real progress sitting
uncommitted for no reason.

Workflow expectations:

- **Commit freely and often** as you complete coherent units of work — don't
  wait for the user to ask, and don't wait for a natural end-of-session
  moment either. Small, well-scoped commits with clear messages beat one
  giant commit at the end.
- Write real commit messages: what changed and why, not just "wip" or
  "updates". Group unrelated changes into separate commits.
- Run `git status` / review the diff before staging broad changes so you
  don't accidentally commit stray or generated files.
- **Do not push, force-push, rewrite history (`rebase -i`, `commit --amend`
  on shared history, `reset --hard`), or touch branches/remotes** without
  explicitly checking with the user first. Local commits are yours to make;
  anything that touches shared/remote state is not.

## Working independently

The steps below are the same whether "given a goal" means picking the next
item off the roadmap or a one-off instruction typed into a chat session with
no plan behind it at all — an ad hoc request is still real development work
on this repo and follows this same loop, commits included.

Unless told otherwise, when given a goal:

1. Make a plan, then work the problem end-to-end without stopping to ask
   permission at each step — pause only for genuinely ambiguous product/design
   decisions, or before anything destructive/irreversible/shared (see git
   rules above).
2. **Verify your own work before calling it done.** Prefer, in order:
   automated checks (`pytest`, `ruff`, `mypy`) for correctness; then actually
   running the app and exercising the feature you built.
3. For UI/UX changes, launch the app (`uv run prismic`) and use computer-use
   to look at it — take a screenshot, interact with the relevant controls
   (click, type, navigate), confirm it behaves and looks right, not just that
   it launches without a traceback.
4. If verification surfaces a bug or a rough edge, fix it and re-verify.
   Loop this (implement -> run checks -> observe via computer-use -> fix)
   until the goal is actually met, not just attempted once.
5. Commit at each meaningful checkpoint along the way, not only at the end —
   if the loop gets interrupted, the history should show real progress.
6. **After every change is done** (not just a UI/UX one -- any change,
   whether or not you personally verified it with computer-use), close any
   running Prismic instance and relaunch it fresh (`uv run prismic`, or with
   a collection path per the launch-path notes below). Leave that instance
   running rather than closing it -- the human will likely want to look at
   the result themselves without having to ask for a relaunch. If a
   verification pass already opened one, that same instance satisfies this
   (no need to close-and-reopen again immediately after). If the human's own
   instance is already open when you start (check `Get-Process`, don't just
   assume), close it by its specific PID (never a blanket
   `taskkill //IM prismic.exe` -- see
   [[feedback-no-blanket-taskkill]] in Claude's memory) and just keep
   working with your own instance from then on for both verification and
   the final hand-back -- no separate throwaway collection/instance dance.
   The human would rather have their window replaced by a working one than
   have it left alone while a second instance runs invisibly alongside.
7. Summarize what changed and how you verified it when you report back.

## 2026-09-16: computer-use + this app's window — root cause found

While scaffolding `tests/gui/`, a Claude session couldn't get computer-use
to show the running `prismic` window. Two separate things were going on,
now both resolved:

1. **Self-inflicted, first.** The session ran
   `taskkill //F //IM prismic.exe` / `//IM python.exe` as "cleanup"
   partway through, which kills every process with that image name
   system-wide — including the user's own just-launched instance. See
   [[feedback-no-blanket-taskkill]] in Claude's memory. Never do this;
   only kill a specific PID you personally spawned and can positively
   identify as orphaned.
2. **A genuine, reproducible timing issue, second.** Launching `prismic`
   via computer-use's own `open_application` (or presumably a normal
   double-click) starts the window unfocused, and it auto-minimizes
   within roughly 1-2 seconds if it never receives real foreground focus
   — likely a focus-stealing-prevention behavior in this environment.
   Because a computer-use tool round trip (launch, then a separate
   screenshot call) always takes longer than that window, every attempt
   to launch-then-screenshot via computer-use alone landed after the
   auto-minimize already happened, making it look like the window never
   rendered at all.

**The fix that works:** launch the app via a native script that doesn't
depend on a second cross-tool round trip — e.g. from PowerShell,
`Start-Process -FilePath "uv" -ArgumentList "run","prismic" -WindowStyle Normal`
— and then take the computer-use screenshot right away. In practice this
launch path reliably stays visible/non-minimized well past the auto-hide
threshold that `open_application` hits, and the window shows up and is
fully interactable (click, type, verify) via the normal
`mcp__computer-use__*` tools. Verified working end-to-end: typed into the
keycap input, saw the keycap boxes render, clicked "Confirm here", saw the
background randomize, closed via the window's own close button.

Takeaway for future sessions: prefer `Start-Process ... -WindowStyle Normal`
(or an equivalent native launch) over `open_application` when you need
computer-use to actually see this app's window. `tests/gui/` (pytest-qt)
remains the reliable, always-available layer for behavioral/state
correctness regardless — it doesn't verify actual on-screen
rendering/visibility, so use computer-use (via the launch path above) when
pixel-level confirmation genuinely matters.

## 2026-09-17: UI theming pass — two more gotchas found via computer-use

Added `ui/theme.py` (a global QSS stylesheet), `ui/thumbnail_provider.py` +
`ui/thumbnail_delegate.py` (async, cached thumbnails for the result list,
built on the existing `WorkerPool`/`FutureWatcher` staleness pattern from
`media/loader.py`), and object-name hooks through `main_window.py`,
`tag_panel.py`, `viewer.py` for the stylesheet to key off. Two more
real bugs surfaced only by actually looking at the running app, not by
`pytest`/`ruff`/`mypy` (all green throughout):

1. **Qt's hex-with-alpha format is `#AARRGGBB` (alpha *first*), not the
   CSS-web `#RRGGBBAA` convention.** Get this backwards — as the theme's
   translucent selection/hover colors originally did (`"#5b93f533"`
   meaning "50/50% blue at ~20% alpha") — and Qt doesn't error; it just
   reads the alpha nibbles as part of the RGB value, silently producing a
   fully-opaque, wrong color. A "20% blue selection wash" rendered as
   solid yellow-green until caught by an actual screenshot. Applies to
   both `QColor("#...")` in Python and colors written directly into QSS.
2. **A `python.exe`/`prismic.exe` computer-use grant is tied to the exact
   resolved executable path, and `uv run` can relink/recreate those paths
   across runs** (observed both as a literal path change and, once, a
   "black window" that was actually computer-use's own masking rectangle
   for an unrecognized process — not a rendering bug at all). If a
   previously-working `request_access` grant for this app's process
   suddenly shows a blank/masked/black window, re-grant that exact
   process name again before assuming the app itself broke — check with a
   direct `QWidget.grab()`-to-PNG from a throwaway script if there's any
   doubt about whether it's a real rendering issue versus a capture/grant
   issue, since that path bypasses computer-use's screen capture (and
   therefore its masking) entirely.

## 2026-09-17: a real bug only a live computer-use pass caught

Reworked the tag UI again per follow-up feedback: `ui/tag_panel.py` now
has a search-to-filter-or-create box and no modal dialogs, row
interaction moved into a new `ui/tag_row_delegate.py` (whole-row click
toggles, hover pencil/trash icons, inline rename via Qt's own editor
flow), and `main_window.py` splits the old single filter panel into two
independent, stacked `TagPanel`s (item tags vs. browse filter) with no
panel left below the viewer. `pytest`/`ruff`/`mypy` were green throughout
-- the bug below only ever showed up by actually clicking the running app.

**Emitting a signal synchronously from inside `QStyledItemDelegate.editorEvent`,
when the handler on the other end resets a model, can corrupt an unrelated
view.** `TagRowDelegate.editorEvent` used to call
`self.toggle_requested.emit(tag_id)` directly on mouse release. The
connected handler chain (`TagPanel` -> `MainWindow._on_filter_toggle` ->
`_refresh_all()`) calls `TagListModel.set_tags()`, which does a
`beginResetModel()/endResetModel()` -- synchronously, while the view was
still mid-dispatch of the very mouse event that triggered it. Reproduced
live: unchecking a filter tag left the *result list* empty and the viewer
on "No collection open" until an unrelated click elsewhere un-stuck it --
selecting a **different** tag worked fine, only checked-to-unchecked
broke, and only via a real click (calling `MainWindow._on_filter_toggle()`
directly in a test never reproduced it, since that skips `editorEvent`
entirely). Fixed by deferring the emission a tick via
`QTimer.singleShot(0, ...)` (`TagRowDelegate._emit_later`), so the click
event finishes unwinding before anything resets a model. Takeaway: a
custom delegate that both handles input *and* triggers a model reset
needs to not do both in the same call stack -- and a passing unit test
that drives the handler method directly, rather than a real click through
the delegate, cannot catch this class of reentrancy bug at all.

Two more launch-path notes from Phase 5's computer-use pass, same root
cause each time (a step that only reveals itself with real interaction,
not automated assertions):

- **`Start-Process -ArgumentList` does not auto-quote array elements.**
  Passing a path containing spaces as a separate array element (e.g.
  `-ArgumentList "run","prismic","C:\...\my data folder"`) silently mangles
  the command line — `Start-Process` joins elements with spaces but does
  **not** wrap ones that need quoting, so the path splits into several
  bogus positional args and the launch fails fast (no window, no error
  surfaced to the caller). Pass one pre-quoted string instead:
  `-ArgumentList 'run prismic "C:\...\my data folder"'`.
- **A GUI keyboard test that sends keys straight to the top-level window
  (`qtbot.keyClick(window, ...)`) is not equivalent to a real user typing
  after clicking somewhere.** It bypasses Qt's actual focus-based event
  delivery, so it can't catch a focused child widget's own key handling
  (e.g. `QAbstractItemView`'s built-in "type to search," which swallowed
  this app's single-letter shortcuts before Phase 5 fixed the keyboard
  wiring to use an application-level event filter). See
  [`phases/05-ui-and-viewer.md`](phases/05-ui-and-viewer.md) for the full
  writeup — this is exactly the class of bug a computer-use pass exists to
  catch that automated tests, as originally written, missed.

## 2026-09-20: shortcuts are a registry now — add them there, not inline

`src/prismic/application/input/shortcuts.py` is the single declaration of
every keyboard shortcut in the app. **Adding a shortcut means adding a
`ShortcutDefinition` to `SHORTCUTS`** — it then appears in the Settings
window (File > Settings…), is rebindable, persists, and shows up in the
hover-explainer bar, all with no further wiring. Hard-coding a key
anywhere else now produces a shortcut the user can see no trace of and
cannot change, which is a regression in this feature, not a shortcut.

Things worth knowing before touching it:

- **Bindings are Qt *portable* key-sequence strings** ("Ctrl+Shift+O",
  "Space", "Left", "Esc"). `ui/keyboard.key_text()` produces them from a
  `QKeyEvent` and `QKeySequence` round-trips them exactly, which is the
  whole reason that format was picked over anything hand-rolled. The
  registry itself stays Qt-free so it's unit-testable without a
  `QApplication`.
- **Two shortcuts sharing a key is sometimes correct.** Focus Mode and
  the viewer's play/pause are both Space by design, resolved by input
  context (overview section 10). That's what `ShortcutScope` is for —
  conflict detection only looks within a scope, so the app's own
  defaults don't get flagged.
- **Not every shortcut is a key combination.** "Tap Ctrl alone" has no
  `QKeySequence` at all; it's `ShortcutKind.TAP_MODIFIER`, recognized
  from a press/release pair in `MainWindow.eventFilter` and edited with
  a modifier chooser rather than a capture box.
- **`MainWindow._apply_bindings()` is the only place an id becomes a real
  key.** It's called at construction and from the Settings dialog's
  `bindings_changed`. Anything new that needs a literal key (a menu
  entry, a button shortcut, a painted label) belongs in there.
- **Tests must not touch the developer's own preferences.** The autouse
  `isolated_preferences` fixture in `tests/conftest.py` redirects the
  config directory by setting the environment variables
  `preferences_directory()` actually reads, rather than patching the
  function, so `test_preferences.py` still exercises the real resolution
  logic.

Two process notes from this pass:

1. **The computer-use masking problem recurred and re-granting did not
   fix it.** `request_access(["Prismic"])` resolved to the correct
   `.venv\Scripts\prismic.exe` path, matching `Get-Process`, and the
   window was still captured as a solid black rectangle — through a
   relaunch, a re-grant, and bringing it to the front from the taskbar.
   (The taskbar's own hover thumbnail rendered the app correctly, which
   is how we know it was masking and not a rendering bug.) **What
   worked instead: a throwaway script that builds the real widgets,
   drives them, and calls `QWidget.grab().save(...)`,** then reading the
   PNGs back. That's the guidance doc's own `QWidget.grab()` suggestion
   promoted from "if there's any doubt" to the primary path when masking
   won't clear — it uses the real widgets and real code paths, and it
   can drive interactions too, so it's a genuine substitute for a
   computer-use pass rather than a consolation prize. It caught the
   drop-down-arrow issue in note 2 below.
2. **A test gap that only the live pass exposed.** Every automated test
   drove `_apply_bindings()` directly, so nothing covered
   `open_settings()` actually connecting the dialog's `bindings_changed`
   signal — a rebind could have been persisted and then ignored by the
   running UI. Found by driving the real window in the grab script and
   noticing the menu action still held its old key. Now tested. The
   general lesson: when a feature has a "record it" half and an "apply
   it" half, test the wire between them explicitly, not just each end.

One Qt/QSS gotcha found while styling the Settings window: **giving a
`QComboBox` any `::drop-down` rule at all suppresses the platform
style's arrow**, and Qt's QSS box model does *not* reproduce the CSS
zero-size-plus-transparent-borders triangle normally used to replace it
— it draws a solid bar instead. Leave both `::drop-down` and
`::down-arrow` unstyled if you want an arrow.

## 2026-09-20: a one-frame flash, and how to find one

The human reported "a very brief flash when opening settings" and noted
it was too fast to see without recording. Screen recording wasn't
needed, and wouldn't have explained it anyway — **the way to diagnose a
flash is to log the window's own events and grab its first frames**,
then diff them. A throwaway script that installs an event filter on the
dialog, prints `geometry()` for every Show/Move/Resize/Paint, and calls
`grab().save()` after `show()` and again after each `processEvents()`
localized both causes in one run. Keep that pattern in mind: a flash is
just a frame that differs from the settled one, and both the geometry
and the pixels are inspectable without a camera.

Two independent causes, both fixed in `ui/settings_dialog.py`:

1. **`QDialog::adjustPosition()` runs twice and the second pass is
   visible.** It only runs while `Qt::WA_Moved` is unset, and it
   positions the dialog once *before* the native window is mapped —
   when the frame margins read as zero — and again once they're real.
   The event log showed a `Move` of (-10, -10) arriving *after* `Show`,
   with the first `Paint` only after that: the window appeared, then
   jumped by its own title bar. The fix is to position it ourselves in
   `__init__`, since calling `move()` at all sets WA_Moved and
   suppresses Qt's version entirely. To place it as well as Qt would
   have, call `create()` first: that builds the native window without
   showing it, which is the point where `windowHandle().frameMargins()`
   becomes real (0/30/0/0 on Windows 11), so the *frame* can be centred
   rather than the client area. Any dialog this app adds later wants
   the same treatment.
2. **A horizontal scrollbar appearing for exactly one frame.** On the
   first layout pass, before the vertical scrollbar's width has come out
   of the viewport, a `QScrollArea`'s content is momentarily too wide;
   the bar appears and then vanishes. `TagPanel` and the result list
   already set `ScrollBarAlwaysOff` for the same underlying reason ("Qt
   reacting to a sub-pixel width miscalculation, not anything actually
   cut off") — that comment turns out to describe a *visible* artifact,
   not just a cosmetic one, and the settings scroll area now does the
   same.

Both are covered by tests that assert the mechanism (the scrollbar
policy; `WA_Moved` plus an unchanged position across `show()`) rather
than pixel coordinates, which vary by screen.

Unrelated defect found while chasing this: `KeyCaptureButton` called
`grabKeyboard()` and only released it on focus-out, so **closing the
Settings window mid-capture could leave an application-wide keyboard
grab held by a hidden widget** — every keystroke in the app going to an
invisible button. Now released in `hideEvent` too.

### Still open: an intermittent hard crash in the test suite

A full `pytest` run has twice ended in a `Windows fatal exception`
faulthandler dump whose frames are all pytest internals (no test frame),
i.e. a fault in C code between tests rather than in any test's Python.
Both times every test had already passed. It has **not** reproduced in
~20 subsequent full runs, randomized and fixed-order, so it wasn't
bisected to a cause and it is **not** known to be related to the
Settings work. Recording it here so the next session doesn't rediscover
it cold.

An attempt to attribute it against the pre-Settings commit (`4aac524`,
via `git worktree`) was made and **produced nothing usable** — worth
knowing so it isn't repeated the same way. Two problems: running
`uv run --project <main repo> pytest` from inside the worktree resolves
the *package* to the main repo's `src/`, so it tested new source against
old tests (the 3 failures were exactly the 3 renamed
`tag_id_for_shortcut` call sites, not a real signal); a worktree needs
its own `uv sync` and a plain `uv run pytest` to be a real baseline. And
more fundamentally, at an observed rate of roughly 2 occurrences in ~25
runs, six clean baseline runs wouldn't have distinguished "absent" from
"didn't happen to fire" anyway. If it resurfaces, catch the dump itself
(the top of the traceback, which run, and whether `-p no:randomly` was
on) rather than trying to prove a negative by repetition. The most likely suspects, untested: Qt
teardown of a widget that still holds a grab (the `grabKeyboard` issue
above is now fixed, which may or may not have been it), or QtMultimedia
/ffmpeg teardown in the viewer tests.
