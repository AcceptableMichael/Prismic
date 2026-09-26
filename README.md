# Prismic

A cross-platform desktop application for viewing and organizing image and video
collections using user-defined tags.

See [`development documents/owned by human/initial technical overview.md`](development%20documents/owned%20by%20human/initial%20technical%20overview.md)
for the full feature requirements and architecture.

## Development setup

This project uses [uv](https://docs.astral.sh/uv/) for Python environment and
dependency management.

```bash
uv sync
```

Run the application:

```bash
uv run prismic
```

Run the test suite:

```bash
uv run pytest
```

Lint and type-check:

```bash
uv run ruff check .
uv run mypy .
```

## Packaging a Windows installer

See [`packaging/README.md`](packaging/README.md) for the full details, but
in short:

```powershell
# Builds the self-contained exe, then also wraps it in a Windows installer
# if Inno Setup is installed (winget install JRSoftware.InnoSetup) --
# otherwise stops after the portable exe.
uv run build
```

Output: `dist\PrismicSetup.exe` -- a per-user installer with a Start Menu
entry, optional desktop icon, uninstaller, and `.prismic` file-association
registration built in. `packaging/README.md` also covers building from an
isolated venv (needed if the dev venv's own `prismic.exe` is locked by a
running instance), verifying the build, and the portable-exe-only
alternative.
