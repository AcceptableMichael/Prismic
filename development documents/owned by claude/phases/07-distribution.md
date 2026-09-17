# Phase 7 — Distribution

Goal: a user can run Prismic on Windows, macOS, or Linux without installing
Python or any dependency themselves. Corresponds to overview sections 8
(cross-platform requirement) and 14.

## Packaging

- [ ] Evaluate and pick a bundling mechanism for a self-contained
      executable/app bundle (e.g. PyInstaller, Nuitka, or Briefcase) —
      document the choice and why here once made
- [ ] Windows build produces a self-contained executable
- [ ] macOS build produces a self-contained app bundle
- [ ] Linux build produces a self-contained executable/bundle
- [ ] Bundled builds correctly include Qt plugins/media codecs needed for
      the Phase 4 supported-format set (this is a common thing bundlers miss
      for Qt Multimedia specifically — verify explicitly, don't assume)

## File type association

Per [`requirements-amendments.md`](../requirements-amendments.md), the
collection artifact is a single `.prismic` file that should open Prismic to
its directory when double-clicked. That requires registering the extension
with each OS during packaging/install — it's not something the file itself
can do.

- [ ] Register `.prismic` as a Prismic document type on Windows (installer-
      driven registry entries) so double-clicking one launches
      `prismic <path>`
- [ ] Register it on macOS via `CFBundleDocumentTypes` in the app bundle's
      `Info.plist`
- [ ] Register it on Linux via a `.desktop` entry and MIME type
      (`xdg-mime`)
- [ ] Verify end-to-end on each platform: double-clicking a `.prismic` file
      in the OS file manager launches Prismic open to the right collection
- [ ] Verify the "already open elsewhere" case (Phase 6) surfaces sensibly
      on each platform rather than silently doing nothing or erroring
      unhelpfully

## Platform verification

- [ ] Media playback (WebM + audio) verified on Windows
- [ ] Media playback verified on macOS
- [ ] Media playback verified on Linux
- [ ] Filesystem behavior (symlink/junction exclusion, path normalization,
      case sensitivity) verified per-platform rather than assumed equivalent
      to whichever platform development happened on
- [ ] Collection locking verified to behave sanely per-platform

## Release process

- [ ] Documented, repeatable build steps for producing all three platform
      artifacts
- [ ] Versioning scheme decided (can align with `pyproject.toml` version)
- [ ] Per `intended use.md`: Claude does not push these anywhere or take any
      internet side effects — the human manages actual distribution/release
      publishing. This phase's scope is "produce a correct local build,"
      not "ship it."
