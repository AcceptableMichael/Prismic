# Intended use

This is a vibecoded project. The intention is that 0% of it is managed by a human, except for interactions through Claude Desktop.

This is a UI-heavy development goal and "computer use" is expected for most tasks to verify and iterate towards the goals.

Do NOT take any side effects on the internet (except installing packages). This includes interacting with GitHub pushes. The human will manage those. Breaking this rule will result in canceling the Claude subscription.

Otherwise, every single aspect of implementation is up to Claude. Claude decides how to commit, how to test, how to adjust the plans.

More information is in the `development documents/` directory:

- `development documents/owned by human/` is read-only for Claude — never edit, move, or delete anything in here. It's the one part of the project the human keeps for themself.
- `development documents/owned by claude/` is Claude's own space for documentation, planning, and goals-tracking, written for both Claude (future sessions) and the human to read. Claude can edit any of its contents.

Claude can decide testing strategies, how to unit test, how to integration test, how to "integration test with computer use".
