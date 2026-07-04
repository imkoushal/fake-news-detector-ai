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


@pytest.fixture(scope="session", autouse=True)
def _init_test_db(tmp_path_factory):
    """Create the auth/analysis schema in an isolated SQLite file for the session.

    The API creates these tables in its FastAPI ``startup`` event, but the test
    suite instantiates ``TestClient(app)`` at module scope (not as a context
    manager), so ``startup`` never fires and the ``users``/``sessions``/``analyses``
    tables are missing. We redirect the SQLite path to a temp dir (``get_db`` reads
    ``backend.db.BASE_DIR`` at call time) and initialise the schema explicitly, so
    DB-backed endpoints work without polluting the repo's ``users.db``.
    """
    from backend import db

    db.BASE_DIR = tmp_path_factory.mktemp("db")
    db.init_auth_db()
    yield


@pytest.fixture(autouse=True)
def _reset_http_client():
    """Isolate the shared httpx client singleton across tests.

    ``backend.http_client._client`` is a lazily-created module-level singleton. In
    the full suite it gets created inside the event loop of whichever test first
    makes an HTTP call (e.g. a TestClient request), then leaks to later tests.
    ``test_close_client`` runs ``asyncio.run(close_client())`` on a fresh loop, so a
    client bound to a prior (now-closed) loop makes ``aclose()`` raise RuntimeError.
    Reset the singleton around each test so no client crosses event loops.
    """
    import backend.http_client as hc

    hc._client = None
    yield
    hc._client = None
