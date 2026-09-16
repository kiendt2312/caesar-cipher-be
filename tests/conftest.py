"""Shared in-memory fixtures for endpoint boundary tests."""

import pytest

from app import config


@pytest.fixture
def exact_limit_bytes() -> bytes:
    """Return a five-MiB payload without creating a repository fixture file."""

    return b"A" * config.MAX_FILE_BYTES


@pytest.fixture
def over_limit_bytes() -> bytes:
    """Return the first payload byte beyond the accepted file-size limit."""

    return b"A" * (config.MAX_FILE_BYTES + 1)
