# Packaging

Repeatable build steps for producing self-contained Prismic builds, plus
per-platform file-association registration. See
[`phases/07-distribution.md`](../development%20documents/owned%20by%20claude/phases/07-distribution.md)
for the full checklist and status; this file just documents *how*, not
*what's done*.

## Bundler choice: PyInstaller

Evaluated PyInstaller, Nuitka, and Briefcase. Picked **PyInstaller**:

- Most mature/battle-tested option for PySide6 specifically, with an
  actively maintained hook (`pyinstaller-hooks-contrib`) that already knows
  how to collect Qt's plugin categories (platforms, styles, imageformats,
  etc.) -- Briefcase's PySide6 support is comparatively newer, and Nuitka's
  Qt handling is more manual/DIY.
- Produces a genuinely self-contained single executable via its "onefile"
  mode, which matches the requirement directly (vs. Briefcase, which is
  oriented around producing installers/app-store bundles rather than a bare
  executable).
- One real gotcha confirmed while building the Windows executable: the
  PySide6 hook does **not** include the Qt Multimedia **ffmpeg** backend
  plugin by default -- only the platform-default "windows" backend, which
  (per the Phase 4 finding, see `bootstrap.py`) cannot decode WebM/VP9/Opus
  at all. `prismic.spec` explicitly adds
  `PySide6/plugins/multimedia/*.dll` to `binaries` to fix this. Verified by
  building without that explicit include first and confirming it's needed,
  not by assumption -- this is exactly the "common thing bundlers miss"
  the phase doc called out in advance.

## Windows build

```powershell
# From the repo root, using the project's normal uv-managed venv:
uv run pyinstaller packaging/prismic.spec --noconfirm

# Or, if pyinstaller isn't installed in your active venv (e.g. because
# another process has the venv's own prismic.exe launcher script locked --
# see the note below), build from an isolated venv instead:
uv venv .venv-build
$env:UV_PROJECT_ENVIRONMENT = ".venv-build"
uv sync --group dev
$env:UV_PROJECT_ENVIRONMENT = $null
.\.venv-build\Scripts\pyinstaller.exe packaging/prismic.spec --noconfirm
```

Output: `dist\prismic.exe` -- a single ~55MB self-contained executable, no
Python install required on the target machine.

**Why an isolated build venv is sometimes needed:** `uv sync`/`uv add`
replaces `.venv\Scripts\prismic.exe` (the entry-point launcher uv itself
generates from `[project.scripts]`), which fails with "Access is denied"
if a Prismic instance built from that venv is currently running -- Windows
locks an executable that's in use. Building from a separate `.venv-build`
sidesteps this entirely rather than requiring you to close whatever's
running the dev venv's own build.

### Verifying the build

Not just "it launches" -- specifically confirm media playback, since that's
where bundling gotchas live:

1. Launch `dist\prismic.exe <path-to-a-folder-with-a-webm>`.
2. Open the WebM, hit Play, and confirm an actual non-black frame renders
   mid-playback (a zoomed screenshot is the reliable way to check this --
   see `project guidance.md`'s computer-use notes). A black frame that
   never changes usually means the ffmpeg plugin didn't get bundled and
   Qt Multimedia silently fell back to a backend that can't decode the
   file.
3. Launch a second instance against the same already-open collection and
   confirm the Phase 6 focus-forwarding behavior still works from the
   packaged exe (no duplicate window, no error dialog) -- the IPC channel
   and file lock are both plain Python/Qt code with no packaging-specific
   risk, but worth a quick confirmation since it wasn't exercised from a
   frozen build before.

## macOS / Linux builds

**Not produced or verified in this environment** -- this repo has so far
only ever been developed and run on Windows (see every prior phase file),
and there's no macOS or Linux machine available to this session. The spec
file (`prismic.spec`) is written to be platform-generic (it derives the
multimedia plugin path from the installed PySide6 package rather than
hardcoding a Windows path), so `pyinstaller packaging/prismic.spec
--noconfirm` run on those platforms *should* produce a working `dist/prismic`
executable/`.app` the same way, but this is untested, not confirmed.

To actually finish this part of Phase 7, a session (or the human) with
access to a real macOS and Linux machine needs to:

- Run the same `pyinstaller packaging/prismic.spec --noconfirm` build on
  each platform and confirm it produces a working, self-contained result
  (on macOS, PyInstaller's `EXE`/onefile settings here produce a bare
  executable, not a `.app` bundle -- switching to a macOS-appropriate
  `BUNDLE()` block, needed for `CFBundleDocumentTypes` file-association
  registration below, is unstarted work).
- Verify WebM/audio playback the same way as the Windows steps above --
  Qt Multimedia's backend selection/plugin bundling is exactly the kind of
  thing that doesn't automatically transfer between platforms.
- Verify collection locking and filesystem behavior (symlink exclusion,
  case sensitivity) per-platform rather than assuming it matches Windows,
  per the Phase 7 checklist.

## File-type association

A build alone doesn't make double-clicking a `.prismic` file launch
Prismic -- the OS needs to be told about the association separately. This
is real, persistent OS/registry state, so it's **not** something a Claude
session registers on your machine automatically. Run these yourself when
you actually want the association active:

- **Windows:** [`windows/register_file_association.ps1`](windows/register_file_association.ps1)
  (and its `unregister_...` counterpart). Registers a per-user
  (`HKCU`, no admin needed) association pointing `.prismic` at
  `dist\prismic.exe`. See the script's own doc comment for details/params.
- **macOS:** not yet written -- needs `CFBundleDocumentTypes` in the app
  bundle's `Info.plist`, which in turn needs the `.app` bundle work noted
  above.
- **Linux:** not yet written -- needs a `.desktop` entry plus
  `xdg-mime default prismic.desktop application/x-prismic` (or similar),
  which needs a real Linux environment to verify against a real file
  manager rather than write blind.

## Versioning

Aligned with `pyproject.toml`'s `[project.version]` (currently `0.1.0`).
No separate packaging-specific version scheme.

## Publishing

Out of scope by design, per `intended use.md`: this produces a correct
local build only. Actually distributing/releasing it (uploading anywhere,
creating a GitHub release, etc.) is the human's call, not something a
Claude session does on its own.
