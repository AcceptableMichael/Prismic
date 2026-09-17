from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "media"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR
