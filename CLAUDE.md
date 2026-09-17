# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repository.

## Intended use

This is a vibecoded project. The intention is that 0% of it is managed by a human, except for interactions through Claude Desktop.

This is a UI-heavy development goal and "computer use" is expected for most tasks to verify and iterate towards the goals.

Do NOT take any side effects on the internet (except installing packages). This includes interacting with GitHub pushes. The human will manage those. Breaking this rule will result in canceling the Claude subscription.

Otherwise, every single aspect of implementation is up to Claude. Claude decides how to commit, how to test, how to adjust the plans.

More information is in the `design docs/` directory. Claude can edit any of the contents. Claude can decide testing strategies, how to unit test, how to integration test, how to "integration test with computer use"

## Project

Prismic is a cross-platform desktop app (Qt/PySide6, Python) for viewing and
tagging image/video collections. Full requirements and architecture are in
[`design docs/initial technical overview.md`](design%20docs/initial%20technical%20overview.md) —
read it before making non-trivial changes. The repository layout and layer
boundaries (`ui/ -> application/ -> domain/ -> persistence|indexing|media/`)
described there are load-bearing; don't collapse them for convenience.

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
