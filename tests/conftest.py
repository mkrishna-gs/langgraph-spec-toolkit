import pytest


@pytest.fixture
def project_dir(tmp_path):
    """A fresh, not-yet-initialized project directory."""
    return tmp_path / "proj"
