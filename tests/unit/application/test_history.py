from prismic.application.commands.base import Command, CommandContext
from prismic.application.history import History


class _RecordingCommand(Command):
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, context: CommandContext) -> None:
        pass

    def undo(self, context: CommandContext) -> None:
        pass


def test_pop_on_empty_history_returns_none() -> None:
    history = History()

    assert history.pop() is None
    assert history.can_undo() is False


def test_push_then_pop_is_lifo() -> None:
    history = History()
    first = _RecordingCommand("first")
    second = _RecordingCommand("second")

    history.push(first)
    history.push(second)

    assert history.pop() is second
    assert history.pop() is first
    assert history.pop() is None


def test_can_undo_reflects_stack_contents() -> None:
    history = History()
    assert history.can_undo() is False

    history.push(_RecordingCommand("a"))
    assert history.can_undo() is True

    history.pop()
    assert history.can_undo() is False


def test_len_reflects_stack_size() -> None:
    history = History()
    history.push(_RecordingCommand("a"))
    history.push(_RecordingCommand("b"))

    assert len(history) == 2

    history.pop()
    assert len(history) == 1
