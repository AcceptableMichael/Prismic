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

Workflow expectations:

- **Commit freely and often** as you complete coherent units of work — don't
  wait for the user to ask. Small, well-scoped commits with clear messages
  beat one giant commit at the end.
- Write real commit messages: what changed and why, not just "wip" or
  "updates". Group unrelated changes into separate commits.
- Run `git status` / review the diff before staging broad changes so you
  don't accidentally commit stray or generated files.
- **Do not push, force-push, rewrite history (`rebase -i`, `commit --amend`
  on shared history, `reset --hard`), or touch branches/remotes** without
  explicitly checking with the user first. Local commits are yours to make;
  anything that touches shared/remote state is not.

## Working independently

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
   it launches without a traceback. Close the app window when done checking.
4. If verification surfaces a bug or a rough edge, fix it and re-verify.
   Loop this (implement -> run checks -> observe via computer-use -> fix)
   until the goal is actually met, not just attempted once.
5. Commit at each meaningful checkpoint along the way, not only at the end —
   if the loop gets interrupted, the history should show real progress.
6. Summarize what changed and how you verified it when you report back.

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
