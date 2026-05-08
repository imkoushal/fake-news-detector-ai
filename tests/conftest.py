"""
Shared test fixtures for pytest.
"""

import sys
from pathlib import Path

import pytest

# Ensure src is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_real_article():
    return (
        "Washington (Reuters) - The Federal Reserve held interest rates steady on "
        "Wednesday and said it would be patient before adjusting them again as it "
        "seeks to make sure the recent slowdown in inflation is temporary. Fed "
        "Chairman Jerome Powell emphasized patience at a news conference after the "
        "meeting. The decision was unanimous. Markets had been focused on what "
        "signals the central bank would give about its next move."
    )


@pytest.fixture
def sample_fake_article():
    return (
        "DOCTORS DON'T WANT YOU TO KNOW: Ancient Himalayan Herb Cures Diabetes in "
        "3 Days! Big Pharma is trying to CENSOR this article! Share before it's "
        "deleted! A revolutionary discovery has sent shockwaves through the medical "
        "establishment. Mainstream media won't report this because pharmaceutical "
        "companies stand to lose BILLIONS! One weird trick that doctors HATE!"
    )


@pytest.fixture
def short_text():
    return "This is too short."


@pytest.fixture
def empty_text():
    return ""


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")
