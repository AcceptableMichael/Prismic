import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "media"


@pytest.fixture
def collection_dir(tmp_path: Path) -> Path:
    """A real collection directory with two supported images in it."""
    root = tmp_path / "vacation"
    root.mkdir()
    shutil.copyfile(FIXTURES_DIR / "supported_image.png", root / "a.png")
    shutil.copyfile(FIXTURES_DIR / "supported_image.png", root / "b.png")
    return root
