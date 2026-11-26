import pytest

from app.db import init_db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Every test gets a fresh database with the sample orders."""
    monkeypatch.setenv("SUPPORT_DB", str(tmp_path / "test.db"))
    init_db()
