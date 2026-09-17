# Phase 7 — Distribution

Goal: a user can run Prismic on Windows, macOS, or Linux without installing
Python or any dependency themselves. Corresponds to overview sections 8
(cross-platform requirement) and 14.

**Status: Windows packaging done and verified; macOS/Linux packaging,
file-association, and platform verification are blocked on not having
access to those platforms from this environment (Windows-only so far,
same as every prior phase) -- see the "What's blocked" section at the
bottom.** Also: registering a `.prismic` file association is a real,
persistent OS registry change, which per the agent safety rules a Claude
session shouldn't make on the human's actual machine on its own initiative
-- see that section too. Build tooling and docs live in
[`packaging/`](../../packaging/README.md).

## Packaging

- [x] Evaluate and pick a bundling mechanism — **PyInstaller**, over
      Nuitka/Briefcase. See [`packaging/README.md`](../../packaging/README.md#bundler-choice-pyinstaller)
      for the full rationale.
- [x] Windows build produces a self-contained executable
      (`packaging/prismic.spec` → `dist/prismic.exe`, ~55MB, no Python
      install required on the target machine)
- [ ] macOS build produces a self-contained app bundle — blocked, no macOS
      access from this environment
- [ ] Linux build produces a self-contained executable/bundle — blocked, no
      Linux access from this environment
- [x] Bundled builds correctly include Qt plugins/media codecs needed for
      the Phase 4 supported-format set — **on Windows**: confirmed the
      common gotcha the phase originally called out is real. PyInstaller's
      PySide6 hook does *not* include the Qt Multimedia ffmpeg backend
      plugin by default (only whatever backend it infers is needed from a
      plain `QApplication` import, which misses "windows" backend can't
      play WebM" entirely). `prismic.spec` explicitly bundles
      `PySide6/plugins/multimedia/*.dll`. Verified live: built without the
      explicit include first, then with it, and only the latter actually
      renders real video frames (confirmed via a zoomed screenshot
      mid-playback of `tests/fixtures/media/audio_video.webm` run through
      the packaged `dist/prismic.exe`, not just the dev venv).

## File type association

Per [`requirements-amendments.md`](../requirements-amendments.md), the
collection artifact is a single `.prismic` file that should open Prismic to
its directory when double-clicked. That requires registering the extension
with each OS during packaging/install — it's not something the file itself
can do.

- [x] Windows: **script written, deliberately not run by this session** —
      [`packaging/windows/register_file_association.ps1`](../../packaging/windows/register_file_association.ps1)
      registers a per-user (`HKCU\Software\Classes`, no admin needed)
      association from `.prismic` to a given `prismic.exe` path, plus an
      `unregister_...` counterpart. Editing the real Windows registry is a
      persistent, machine-wide (well, per-user) OS setting change — outside
      what an agent should do on its own on a real machine per the
      standing safety rules, even inside an otherwise-autonomous project.
      The script itself is real, reviewed code, not a stub; a human runs it
      when they actually want the association active.
- [ ] macOS: not started — needs `CFBundleDocumentTypes` in an `Info.plist`,
      which needs the still-unstarted macOS `.app` bundle work first (see
      Packaging above)
- [ ] Linux: not started — needs a `.desktop` entry + `xdg-mime`, needs a
      real Linux environment to verify against an actual file manager
- [ ] Verify end-to-end on each platform: double-clicking a `.prismic` file
      in the OS file manager launches Prismic open to the right collection
      — **not done even for Windows**, since it requires the registration
      script above to have actually been run on a real machine, which this
      session deliberately didn't do. `bootstrap.py`'s argv-path handling
      (the code path a double-click launch actually exercises) is already
      covered by `tests/gui/test_main_window.py` and Phase 6's end-to-end
      tests — what's specifically unverified is the OS shell's own
      double-click → process-launch mechanism, since that only exists once
      the registry keys are in place.
- [x] Verify the "already open elsewhere" case (Phase 6) surfaces sensibly:
      verified on Windows against the packaged `dist/prismic.exe` (not just
      the dev venv) — launched two instances against the same collection,
      confirmed the second one self-closed after focusing the first, no
      duplicate window and no error dialog, matching the Phase 6 addendum
      behavior exactly.

## Platform verification

- [x] Media playback (WebM + audio) verified on Windows — see Packaging
      above
- [ ] Media playback verified on macOS — blocked, no macOS access
- [ ] Media playback verified on Linux — blocked, no Linux access
- [ ] Filesystem behavior (symlink/junction exclusion, path normalization,
      case sensitivity) verified per-platform — Windows behavior was
      already exercised throughout Phases 1-6; macOS/Linux specifically
      blocked here
- [x] Collection locking verified to behave sanely on Windows (this is a
      re-confirmation of Phase 6's `tests/integration/test_locking.py`
      against the packaged build specifically, not new coverage)
- [ ] Collection locking verified on macOS/Linux — blocked

## Release process

- [x] Documented, repeatable build steps — [`packaging/README.md`](../../packaging/README.md)
- [x] Versioning scheme decided — aligned with `pyproject.toml`'s
      `[project.version]` (`0.1.0`), no separate packaging-specific scheme
- [x] Per `intended use.md`: no internet side effects taken, nothing
      pushed/published — build output stayed local (`dist/`, gitignored)

## What's blocked, and why

Two different kinds of "not done" here, worth keeping distinct:

1. **Environment-blocked (macOS/Linux everything):** this project has, per
   every prior phase file, only ever run on a single Windows machine. There
   is no macOS or Linux access available to build or verify against. This
   isn't a design gap — the Windows work (spec file, plugin bundling fix,
   association script) is written to generalize (the spec derives paths
   from the installed PySide6 package rather than hardcoding Windows
   specifics), but "should generalize" and "verified to work" are
   different claims, and only the Windows one is backed by an actual run.
2. **Deliberately not self-executed (Windows file-association
   registration):** unlike almost everything else in this project, this
   one step edits real, persistent state on the actual machine outside the
   repo/venv sandbox — the Windows registry. The standing agent safety
   rules treat "modifying system settings" as something to hand to the
   human rather than do autonomously, even where a project's own
   `intended use.md` grants broad autonomy generally. The script is
   written, reviewed, and ready; running it is a one-line, deliberate
   choice for a human to make, not something this session did on its own.

## Tests

Packaging isn't really unit-testable in the usual sense (there's no
meaningful way to pytest a PyInstaller build without actually invoking
PyInstaller, which is slow and not something to run on every `pytest`
invocation). Verification here is scripted-but-manual, same spirit as
Phase 6's computer-use pass:

- [x] Windows build launched via computer-use, opened a real scratch
      collection (fresh folder, not `my data folder`), confirmed the file
      list rendered
- [x] Played a real WebM+audio fixture through the packaged build and
      confirmed actual frame rendering (not just "no crash") via a zoomed
      screenshot mid-playback
- [x] Ran the two-instance locked-collection scenario against the packaged
      build and confirmed Phase 6's focus-forwarding behavior holds
- [ ] OS-level double-click launch — needs the registration script to have
      actually been run; see above
- [ ] Anything macOS/Linux — blocked, see above
