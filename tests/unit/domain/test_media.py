from prismic.domain.media import Media, MediaState


def test_media_is_a_plain_value_type() -> None:
    media = Media(
        id=1,
        relative_path="photos/cat.jpg",
        content_hash="abc123",
        size=1024,
        mtime=1_700_000_000.0,
        state=MediaState.ACTIVE,
    )
    assert media.id == 1
    assert media.relative_path == "photos/cat.jpg"
    assert media.state is MediaState.ACTIVE


def test_state_values_round_trip_through_their_string_form() -> None:
    assert MediaState("active") is MediaState.ACTIVE
    assert MediaState("missing") is MediaState.MISSING
