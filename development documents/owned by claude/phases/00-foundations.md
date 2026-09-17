# Phase 0 — Foundations

Goal: a working toolchain, project skeleton, and verification workflow to
build everything else on top of. Most of this already exists; this file
records what's done and what's still owed before Phase 1 starts in earnest.

## Toolchain & project skeleton

- [x] `uv`-managed project (`pyproject.toml`, `uv.lock`, `.python-version`)
- [x] `pyside6` dependency and `prismic` console-script entry point
- [x] `ruff` configured (lint + format)
- [x] `mypy` configured in strict mode
- [x] `pytest` + `pytest-qt` configured, `tests/{unit,integration,gui,fixtures}`
      layout exists
- [x] Package skeleton matches the layer boundaries from the architecture doc
      (`application/`, `domain/`, `persistence/`, `indexing/`, `media/`,
      `ui/`) — currently empty stubs except `ui/`, which is fine at this
      stage
- [x] App launches (`uv run prismic`) and shows a window

## Verification workflow

- [x] Confirm pytest-qt tests actually run and pass (`uv run pytest`)
- [x] Confirm computer-use can reliably see and interact with the app window
      — resolved via the `Start-Process -WindowStyle Normal` launch path
      documented in [`project guidance.md`](../project%20guidance.md); do not
      rediscover this the hard way in a future session
- [x] Confirm `ruff check`, `ruff format --check`, `mypy .` all run clean on
      the current skeleton

## Cleanup before Phase 1

- [ ] Remove or repurpose the placeholder keycap/background-randomizer demo
      in [`main_window.py`](../../../src/prismic/ui/main_window.py) once
      Phase 5 needs the window for real UI — no need to do this early, just
      don't let it get mistaken for real functionality
- [ ] Decide and document the minimum supported OS/Python patch versions if
      this becomes relevant for packaging (can defer to Phase 7)
