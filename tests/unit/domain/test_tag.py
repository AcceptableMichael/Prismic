import pytest

from prismic.domain.tag import InvalidTagNameError, Tag, validate_tag_name


def test_trims_surrounding_whitespace() -> None:
    assert validate_tag_name("  vacation  ") == "vacation"


def test_rejects_empty_after_trim() -> None:
    with pytest.raises(InvalidTagNameError):
        validate_tag_name("   ")


def test_rejects_newline() -> None:
    with pytest.raises(InvalidTagNameError):
        validate_tag_name("multi\nline")


def test_rejects_carriage_return() -> None:
    with pytest.raises(InvalidTagNameError):
        validate_tag_name("multi\rline")


def test_allows_unicode() -> None:
    assert validate_tag_name("日本語") == "日本語"


def test_is_case_sensitive_at_the_value_level() -> None:
    assert validate_tag_name("Vacation") != validate_tag_name("vacation")


def test_tag_is_a_plain_value_type() -> None:
    tag = Tag(id=1, name="vacation")
    assert tag.id == 1
    assert tag.name == "vacation"
