import pytest

import engine


@pytest.fixture(autouse=True)
def no_real_waits(monkeypatch):
    """Fill verification polls Kalshi with a delay in production; tests must not pay it."""
    monkeypatch.setattr(engine, "FILL_RETRY_DELAY", 0)
