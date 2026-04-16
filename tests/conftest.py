"""Shared pytest fixtures for 필케어 tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).parent.parent / "data"
