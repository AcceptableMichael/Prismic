from prismic.application.tag_recency import TagRecencyTracker
from prismic.domain.tag import Tag

_A = Tag(id=1, name="a")
_B = Tag(id=2, name="b")
_C = Tag(id=3, name="c")


def test_unclicked_tags_keep_their_given_order() -> None:
    tracker = TagRecencyTracker(_clock=lambda: 0.0)

    assert tracker.order([_A, _B, _C]) == [_A, _B, _C]


def test_a_recently_clicked_tag_moves_to_the_front() -> None:
    clock = [0.0]
    tracker = TagRecencyTracker(_clock=lambda: clock[0])

    tracker.record_click(_C.id)

    assert tracker.order([_A, _B, _C]) == [_C, _A, _B]


def test_within_the_recent_group_most_recently_clicked_comes_first() -> None:
    clock = [0.0]
    tracker = TagRecencyTracker(_clock=lambda: clock[0])

    tracker.record_click(_A.id)
    clock[0] = 10.0
    tracker.record_click(_B.id)

    assert tracker.order([_A, _B, _C]) == [_B, _A, _C]


def test_a_click_older_than_30_minutes_no_longer_counts_as_recent() -> None:
    clock = [0.0]
    tracker = TagRecencyTracker(_clock=lambda: clock[0])

    tracker.record_click(_A.id)
    clock[0] = 30 * 60 + 1

    assert tracker.order([_A, _B, _C]) == [_A, _B, _C]


def test_a_click_exactly_30_minutes_ago_still_counts_as_recent() -> None:
    clock = [0.0]
    tracker = TagRecencyTracker(_clock=lambda: clock[0])

    tracker.record_click(_A.id)
    clock[0] = 30 * 60

    assert tracker.order([_A, _B, _C]) == [_A, _B, _C]


def test_reclicking_a_tag_refreshes_its_recency() -> None:
    clock = [0.0]
    tracker = TagRecencyTracker(_clock=lambda: clock[0])

    tracker.record_click(_A.id)
    clock[0] = 10.0
    tracker.record_click(_B.id)
    clock[0] = 20.0
    tracker.record_click(_A.id)

    assert tracker.order([_A, _B, _C]) == [_A, _B, _C]
