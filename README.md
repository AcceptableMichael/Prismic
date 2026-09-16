# Prismic

A cross-platform desktop application for viewing and organizing image and video
collections using user-defined tags.

See [`design docs/initial technical overview.md`](design%20docs/initial%20technical%20overview.md)
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
