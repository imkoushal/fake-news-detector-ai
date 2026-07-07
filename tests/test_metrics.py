"""
§5 growth-metrics tests (backend/metrics.py).

Covers log_event durability, the RAG cost estimate, and every derived metric in
compute_metrics — totals, activation, D7 retention, viral coefficient, and
cost-per-check. Runs fully offline against the session's temp SQLite DB.

Cohort-sensitive metrics (retention, "in window" counts) depend on
``created_at``. Rather than sleep, we insert rows with an explicit timestamp via
a small helper so the tests are deterministic.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend import metrics  # noqa: E402
from backend.db import execute_db, ph  # noqa: E402


def _stamp(days_ago: float) -> str:
    """A DB timestamp string ``days_ago`` days in the past."""
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _insert(event_type, *, user_id=None, source="web", cost_usd=0.0, days_ago=0.0):
    """Insert one event with an explicit created_at (bypasses the DB default)."""
    execute_db(
        f"INSERT INTO metric_events (event_type, user_id, source, cost_usd, created_at) "
        f"VALUES ({ph(5)})",
        (event_type, user_id, source, cost_usd, _stamp(days_ago)),
        commit=True,
    )


@pytest.fixture(autouse=True)
def _clean_metrics_table():
    """Ensure the table exists and start every test from an empty slate."""
    metrics.init_metrics_db()
    execute_db("DELETE FROM metric_events", commit=True)
    yield
    execute_db("DELETE FROM metric_events", commit=True)


# ── log_event ──────────────────────────────────────────────────────────────

def test_log_event_persists_row():
    metrics.log_event(metrics.EVENT_CHECK, user_id=1, source="web", cost_usd=0.0003,
                      meta={"path": "rag"})
    row = execute_db(
        f"SELECT event_type, user_id, source, cost_usd, meta FROM metric_events "
        f"WHERE user_id = {ph()}",
        (1,), fetch="one",
    )
    assert row is not None
    assert row[0] == metrics.EVENT_CHECK
    assert row[1] == 1
    assert row[2] == "web"
    assert abs(float(row[3]) - 0.0003) < 1e-9
    assert '"path":"rag"' in row[4]


def test_log_event_never_raises_on_bad_input(monkeypatch):
    """A DB failure inside log_event must be swallowed, not propagated."""
    def _boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(metrics, "execute_db", _boom)
    # Should not raise despite the underlying failure.
    metrics.log_event(metrics.EVENT_SIGNUP, user_id=99)


# ── cost estimate ────────────────────────────────────────────────────────────

def test_estimate_rag_cost_adds_components(monkeypatch):
    monkeypatch.setattr(metrics, "GROQ_COST_PER_CALL", 0.0003)
    monkeypatch.setattr(metrics, "GNEWS_COST_PER_CALL", 0.001)
    assert metrics.estimate_rag_cost(groq_calls=1, gnews_calls=0) == pytest.approx(0.0003)
    assert metrics.estimate_rag_cost(groq_calls=2, gnews_calls=1) == pytest.approx(0.0016)


# ── totals & cost-per-check ──────────────────────────────────────────────────

def test_totals_and_cost_per_check():
    _insert(metrics.EVENT_SIGNUP, user_id=1, days_ago=1)
    _insert(metrics.EVENT_CHECK, user_id=1, source="web", cost_usd=0.0003, days_ago=1)
    _insert(metrics.EVENT_CHECK, user_id=1, source="telegram", cost_usd=0.0001, days_ago=1)
    _insert(metrics.EVENT_SHARE, user_id=1, days_ago=1)

    m = metrics.compute_metrics(window_days=30)
    assert m["available"] is True
    assert m["totals"]["signups"] == 1
    assert m["totals"]["checks"] == 2
    assert m["totals"]["shares"] == 1
    assert m["totals"]["checks_by_source"] == {"web": 1, "telegram": 1}
    assert m["cost"]["total_usd"] == pytest.approx(0.0004)
    assert m["cost"]["per_check_usd"] == pytest.approx(0.0002)


def test_window_excludes_old_events():
    _insert(metrics.EVENT_CHECK, user_id=1, days_ago=100)  # outside 30d window
    _insert(metrics.EVENT_CHECK, user_id=1, days_ago=2)    # inside
    m = metrics.compute_metrics(window_days=30)
    assert m["totals"]["checks"] == 1


# ── activation ───────────────────────────────────────────────────────────────

def test_activation_rate():
    # User 1 signs up AND checks -> activated. User 2 signs up only -> not.
    _insert(metrics.EVENT_SIGNUP, user_id=1, days_ago=3)
    _insert(metrics.EVENT_CHECK, user_id=1, days_ago=2)
    _insert(metrics.EVENT_SIGNUP, user_id=2, days_ago=3)

    m = metrics.compute_metrics(window_days=30)
    assert m["activation"]["signed_up"] == 2
    assert m["activation"]["activated"] == 1
    assert m["activation"]["rate"] == pytest.approx(0.5)


# ── viral coefficient ────────────────────────────────────────────────────────

def test_viral_coefficient():
    for _ in range(4):
        _insert(metrics.EVENT_CHECK, user_id=1, days_ago=1)
    for _ in range(2):
        _insert(metrics.EVENT_SHARE, user_id=1, days_ago=1)
    m = metrics.compute_metrics(window_days=30)
    assert m["viral"]["coefficient"] == pytest.approx(0.5)


def test_zero_checks_no_division_error():
    m = metrics.compute_metrics(window_days=30)
    assert m["available"] is True
    assert m["viral"]["coefficient"] == 0.0
    assert m["cost"]["per_check_usd"] == 0.0
    assert m["activation"]["rate"] == 0.0


# ── D7 retention ─────────────────────────────────────────────────────────────

def test_d7_retention_counts_returning_user():
    # User 1: first seen 10d ago, returns 3d later (within 7d) -> retained.
    _insert(metrics.EVENT_SIGNUP, user_id=1, days_ago=10)
    _insert(metrics.EVENT_CHECK, user_id=1, days_ago=7)
    # User 2: first seen 10d ago, never returns -> in cohort, not retained.
    _insert(metrics.EVENT_SIGNUP, user_id=2, days_ago=10)

    m = metrics.compute_metrics(window_days=30)
    d7 = m["retention_d7"]
    assert d7["cohort"] == 2
    assert d7["retained"] == 1
    assert d7["rate"] == pytest.approx(0.5)


def test_d7_retention_excludes_too_recent_users():
    # First seen 3d ago — no full 7-day window yet, excluded from cohort.
    _insert(metrics.EVENT_SIGNUP, user_id=1, days_ago=3)
    _insert(metrics.EVENT_CHECK, user_id=1, days_ago=2)
    m = metrics.compute_metrics(window_days=30)
    assert m["retention_d7"]["cohort"] == 0


def test_d7_retention_same_day_return_not_counted():
    # Two events on the same first day don't count as "returning".
    _insert(metrics.EVENT_SIGNUP, user_id=1, days_ago=10)
    _insert(metrics.EVENT_CHECK, user_id=1, days_ago=10)
    m = metrics.compute_metrics(window_days=30)
    assert m["retention_d7"]["cohort"] == 1
    assert m["retention_d7"]["retained"] == 0
