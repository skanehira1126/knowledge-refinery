from pathlib import Path

import pytest


@pytest.fixture
def refinery_root(tmp_path: Path) -> Path:
    root = tmp_path / ".refinery"
    root.mkdir(parents=True, exist_ok=True)
    return root
