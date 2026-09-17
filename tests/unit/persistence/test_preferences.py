from prismic.persistence.preferences import preferences_directory, preferences_file_path


def test_preferences_directory_is_named_after_the_app() -> None:
    assert preferences_directory().name.lower() == "prismic"


def test_preferences_file_lives_inside_the_preferences_directory() -> None:
    assert preferences_file_path().parent == preferences_directory()


def test_preferences_location_is_outside_any_collection() -> None:
    # It's app-wide state, not per-collection — it must never live under a
    # collection root, unlike the `.prismic` database file.
    assert preferences_file_path().suffix != ".prismic"
