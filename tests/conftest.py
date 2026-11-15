from pathlib import Path

import pytest


@pytest.fixture
def make_file(tmp_path: Path):
    """Create a file below tmp_path with the given content."""

    def _make(relative: str, content: bytes) -> Path:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    return _make
