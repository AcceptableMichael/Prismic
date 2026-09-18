"""Console-script wrappers around the build steps documented in
packaging/README.md.

uv has no separate task-runner feature (no npm-style "scripts" block) --
`uv run <name>` just runs whatever `[project.scripts]` entry point (or
any other command) is on the project's venv PATH. These two functions are
registered as `prismic-build-exe` / `prismic-installer` in pyproject.toml
so the two-step packaging flow is `uv run prismic-build-exe` followed by
`uv run prismic-installer`, instead of remembering the underlying
PyInstaller/Inno Setup invocations.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def build_exe() -> None:
    """Build dist/prismic.exe via PyInstaller. See packaging/prismic.spec."""
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "packaging/prismic.spec", "--noconfirm"],
        cwd=REPO_ROOT,
        check=True,
    )


def build_installer() -> None:
    """Wrap dist/prismic.exe into dist/PrismicSetup.exe via Inno Setup.

    Requires dist/prismic.exe to already exist -- run `build_exe` (i.e.
    `uv run prismic-build-exe`) first.
    """
    iscc = shutil.which("iscc") or shutil.which("ISCC")
    if iscc is None:
        default = Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe"
        if default.exists():
            iscc = str(default)
    if iscc is None:
        raise SystemExit(
            "ISCC.exe not found on PATH or at the default Inno Setup install "
            "location (%s). Install it with `winget install "
            "JRSoftware.InnoSetup`, then re-run, or invoke ISCC.exe "
            "directly -- see packaging/README.md." % default
        )
    subprocess.run([iscc, "packaging/windows/prismic.iss"], cwd=REPO_ROOT, check=True)
