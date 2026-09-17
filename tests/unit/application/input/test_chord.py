from prismic.application.input.chord import ChordState


def test_starts_with_nothing_pending() -> None:
    chord = ChordState()

    assert chord.is_pending is False
    assert chord.pending_keys == ()


def test_press_accumulates_pending_keys() -> None:
    chord = ChordState()

    chord.press("g")
    chord.press("g")

    assert chord.pending_keys == ("g", "g")
    assert chord.is_pending is True


def test_match_on_an_exact_chord_returns_the_command_and_clears() -> None:
    chord = ChordState()
    chords: dict[tuple[str, ...], str] = {("g", "g"): "go_to_start"}
    chord.press("g")
    chord.press("g")

    result = chord.match(chords)

    assert result == "go_to_start"
    assert chord.is_pending is False


def test_match_on_a_valid_prefix_returns_none_and_stays_pending() -> None:
    chord = ChordState()
    chords: dict[tuple[str, ...], str] = {("g", "g"): "go_to_start"}
    chord.press("g")

    result = chord.match(chords)

    assert result is None
    assert chord.is_pending is True


def test_match_on_a_dead_end_cancels() -> None:
    chord = ChordState()
    chords: dict[tuple[str, ...], str] = {("g", "g"): "go_to_start"}
    chord.press("x")

    result = chord.match(chords)

    assert result is None
    assert chord.is_pending is False


def test_advance_time_within_timeout_does_not_cancel() -> None:
    chord = ChordState(timeout_seconds=1.0)
    chord.press("g")

    timed_out = chord.advance_time(0.5)

    assert timed_out is False
    assert chord.is_pending is True


def test_advance_time_past_timeout_cancels() -> None:
    chord = ChordState(timeout_seconds=1.0)
    chord.press("g")

    timed_out = chord.advance_time(1.5)

    assert timed_out is True
    assert chord.is_pending is False


def test_advance_time_with_nothing_pending_is_a_no_op() -> None:
    chord = ChordState()

    assert chord.advance_time(10.0) is False


def test_a_new_key_press_resets_the_timeout_clock() -> None:
    chord = ChordState(timeout_seconds=1.0)
    chord.press("g")

    chord.advance_time(0.9)
    chord.press("g")  # resets the clock
    timed_out = chord.advance_time(0.9)

    assert timed_out is False
    assert chord.pending_keys == ("g", "g")


def test_cancel_clears_pending_state() -> None:
    chord = ChordState()
    chord.press("g")

    chord.cancel()

    assert chord.is_pending is False
    assert chord.pending_keys == ()
