"""Console-script wrappers around the build steps documented in
packaging/README.md.

uv has no separate task-runner feature (no npm-style "scripts" block) --
`uv run <name>` just runs whatever `[project.scripts]` entry point (or
any other command) is on the project's venv PATH. These functions are
registered as `build` / `prismic-installer` in pyproject.toml. `build`
(`uv run build`) runs the whole packaging flow -- PyInstaller, then the
Inno Setup wrapping step if Inno Setup is available -- so a single `uv run
build` is normally all that's needed. Note this shadows `uv`'s own
built-in `uv build` (which produces the wheel/sdist via the hatchling
backend, unrelated to this) -- the two are invoked differently (`uv run
build` vs `uv build`) but the name similarity is intentional shorthand,
not a mistake. `prismic-installer` remains as a standalone entry point for
re-wrapping an existing dist/prismic.exe (e.g. after installing Inno Setup
without rebuilding the exe), instead of remembering the underlying
PyInstaller/Inno Setup invocations.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def build_exe() -> None:
    """Build dist/prismic.exe via PyInstaller, then wrap it into
    dist/PrismicSetup.exe via Inno Setup if Inno Setup is available.

    See packaging/prismic.spec. The installer step is skipped (with a
    note, not an error) when Inno Setup isn't installed, since the
    portable exe is a complete, usable result on its own.
    """
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "packaging/prismic.spec", "--noconfirm"],
        cwd=REPO_ROOT,
        check=True,
    )
    iscc = _find_iscc()
    if iscc is None:
        print(
            "Inno Setup not found -- skipping installer step. "
            "dist/prismic.exe is ready to use as-is; install Inno Setup "
            "(`winget install JRSoftware.InnoSetup`) and run "
            "`uv run prismic-installer` to also produce dist/PrismicSetup.exe."
        )
        return
    _run_inno_setup(iscc)


def build_installer() -> None:
    """Wrap dist/prismic.exe into dist/PrismicSetup.exe via Inno Setup.

    Requires dist/prismic.exe to already exist -- run `build_exe` (i.e.
    `uv run build`) first. Unlike the installer step folded
    into `build_exe`, this raises if Inno Setup isn't found, since it's
    invoked specifically to produce the installer.
    """
    iscc = _find_iscc()
    if iscc is None:
        default = Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe"
        raise SystemExit(
            "ISCC.exe not found on PATH or at the default Inno Setup install "
            "location (%s). Install it with `winget install "
            "JRSoftware.InnoSetup`, then re-run, or invoke ISCC.exe "
            "directly -- see packaging/README.md." % default
        )
    _run_inno_setup(iscc)


def _find_iscc() -> str | None:
    iscc = shutil.which("iscc") or shutil.which("ISCC")
    if iscc is not None:
        return iscc
    default = Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe"
    if default.exists():
        return str(default)
    return None


def _run_inno_setup(iscc: str) -> None:
    subprocess.run([iscc, "packaging/windows/prismic.iss"], cwd=REPO_ROOT, check=True)
