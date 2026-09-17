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
