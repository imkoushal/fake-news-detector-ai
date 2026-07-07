"""
§5 growth metrics — activation, retention, viral coefficient, cost-per-check.

A single append-only ``metric_events`` table records the raw funnel events
(signup / check / share) plus per-event cost. All rates are derived on read in
``compute_metrics`` so we never store denormalized numbers that can drift.

Design rules (match the ROADMAP "for me" constraints):
- **Never break a request.** ``log_event`` swallows every error — a metrics
  write failing must not fail an analysis or a signup.
- **Portable.** Uses the same ``execute_db`` / ``ph`` helpers as the rest of the
  backend, so it runs on SQLite (local) and PostgreSQL (Render) unchanged.
- **Cheap.** One indexed insert per event; reads are admin-only and windowed.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta

from backend.db import execute_db, ph, USE_POSTGRES

logger = logging.getLogger("fake_news_api")

# Event type vocabulary (kept small on purpose).
EVENT_SIGNUP = "signup"
EVENT_CHECK = "check"
EVENT_SHARE = "share"

# Per-call cost estimates for the RAG path, overridable by env so the numbers
# stay honest as provider pricing changes. Defaults are deliberately tiny —
# Groq's gpt-oss-120b and the GNews free tier are near-zero per call today.
GROQ_COST_PER_CALL = float(os.getenv("METRIC_GROQ_COST", "0.0003"))
GNEWS_COST_PER_CALL = float(os.getenv("METRIC_GNEWS_COST", "0.0"))


def init_metrics_db() -> None:
    """Create the ``metric_events`` table and its indexes if absent."""
    conn = None
    try:
        from backend.db import get_db

        conn = get_db()
        c = conn.cursor()
        if USE_POSTGRES:
            c.execute(
                """CREATE TABLE IF NOT EXISTS metric_events (
                    id SERIAL PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id INTEGER,
                    anon_id TEXT,
                    source TEXT DEFAULT 'web',
                    cost_usd REAL DEFAULT 0,
                    meta TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )
        else:
            c.execute(
                """CREATE TABLE IF NOT EXISTS metric_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    user_id INTEGER,
                    anon_id TEXT,
                    source TEXT DEFAULT 'web',
                    cost_usd REAL DEFAULT 0,
                    meta TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )"""
            )
        c.execute("CREATE INDEX IF NOT EXISTS idx_metric_events_type ON metric_events(event_type)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_metric_events_created ON metric_events(created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_metric_events_user ON metric_events(user_id)")
        conn.commit()
        logger.info("metric_events table ready")
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"init_metrics_db failed (metrics disabled): {e}")
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def log_event(
    event_type: str,
    *,
    user_id: int | None = None,
    anon_id: str | None = None,
    source: str = "web",
    cost_usd: float = 0.0,
    meta: dict | None = None,
) -> None:
    """Record one funnel event. Never raises — metrics must not break a request."""
    try:
        meta_json = json.dumps(meta, separators=(",", ":")) if meta else None
        execute_db(
            f"INSERT INTO metric_events (event_type, user_id, anon_id, source, cost_usd, meta) "
            f"VALUES ({ph(6)})",
            (event_type, user_id, anon_id, source, float(cost_usd or 0.0), meta_json),
            commit=True,
        )
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"log_event({event_type}) failed: {e}")


def estimate_rag_cost(*, groq_calls: int = 1, gnews_calls: int = 1) -> float:
    """Estimated USD cost of one RAG verification (GNews search + Groq LLM)."""
    return groq_calls * GROQ_COST_PER_CALL + gnews_calls * GNEWS_COST_PER_CALL


def _cutoff(days: int) -> str:
    """A space-separated timestamp string that sorts correctly against
    ``CURRENT_TIMESTAMP`` columns on both SQLite and PostgreSQL."""
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def _to_dt(value) -> datetime | None:
    """Coerce a DB timestamp (datetime on PG, str on SQLite) to a datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip().replace("T", " ")
    # Drop timezone/fractional noise we don't need for day-granularity math.
    s = s.split("+")[0].split(".")[0].strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _count(event_type: str, since: str) -> int:
    row = execute_db(
        f"SELECT COUNT(*) FROM metric_events WHERE event_type = {ph()} AND created_at >= {ph()}",
        (event_type, since),
        fetch="one",
    )
    return int(row[0]) if row and row[0] is not None else 0


def compute_metrics(window_days: int = 30) -> dict:
    """Compute the §5 growth metrics over the trailing ``window_days``.

    Returns a JSON-serializable dict. On any query failure returns
    ``{"available": False}`` rather than raising, so the admin endpoint degrades
    gracefully before the table has data.
    """
    try:
        since = _cutoff(window_days)

        # ── Raw volumes in the window ──
        signups = _count(EVENT_SIGNUP, since)
        checks = _count(EVENT_CHECK, since)
        shares = _count(EVENT_SHARE, since)

        cost_row = execute_db(
            f"SELECT COALESCE(SUM(cost_usd), 0) FROM metric_events "
            f"WHERE event_type = {ph()} AND created_at >= {ph()}",
            (EVENT_CHECK, since),
            fetch="one",
        )
        total_cost = float(cost_row[0]) if cost_row and cost_row[0] is not None else 0.0

        checks_by_source = dict(
            execute_db(
                f"SELECT source, COUNT(*) FROM metric_events "
                f"WHERE event_type = {ph()} AND created_at >= {ph()} GROUP BY source",
                (EVENT_CHECK, since),
                fetch="all",
            )
            or []
        )

        # ── Activation: signed-up users (in window) who ran ≥1 check (ever) ──
        signed_up_users = [
            r[0]
            for r in (
                execute_db(
                    f"SELECT DISTINCT user_id FROM metric_events "
                    f"WHERE event_type = {ph()} AND created_at >= {ph()} AND user_id IS NOT NULL",
                    (EVENT_SIGNUP, since),
                    fetch="all",
                )
                or []
            )
        ]
        activated = 0
        for uid in signed_up_users:
            hit = execute_db(
                f"SELECT 1 FROM metric_events WHERE event_type = {ph()} AND user_id = {ph()} LIMIT 1",
                (EVENT_CHECK, uid),
                fetch="one",
            )
            if hit:
                activated += 1
        activation_rate = round(activated / len(signed_up_users), 4) if signed_up_users else 0.0

        # ── D7 retention: of users first seen 7-60d ago, % who returned on a
        #    later day within 7 days of first activity. Computed in Python from
        #    raw (user, timestamp) rows to stay portable across SQLite/PG. ──
        d7 = _compute_d7_retention()

        # ── Viral coefficient: shares per check (ROADMAP's definition). ──
        viral_coefficient = round(shares / checks, 4) if checks else 0.0

        cost_per_check = round(total_cost / checks, 6) if checks else 0.0

        return {
            "available": True,
            "window_days": window_days,
            "generated_at": datetime.now().isoformat(),
            "totals": {
                "signups": signups,
                "checks": checks,
                "shares": shares,
                "checks_by_source": {str(k): int(v) for k, v in checks_by_source.items()},
            },
            "activation": {
                "signed_up": len(signed_up_users),
                "activated": activated,
                "rate": activation_rate,
                "definition": "% of users who signed up in the window and ran >=1 check",
            },
            "retention_d7": d7,
            "viral": {
                "shares": shares,
                "checks": checks,
                "coefficient": viral_coefficient,
                "definition": "shares per check; <1 means the sharing loop needs work",
            },
            "cost": {
                "total_usd": round(total_cost, 6),
                "per_check_usd": cost_per_check,
                "note": "estimated from METRIC_GROQ_COST / METRIC_GNEWS_COST env vars",
            },
        }
    except Exception as e:
        logger.error(f"compute_metrics failed: {e}")
        return {"available": False, "error": "metrics temporarily unavailable"}


def _compute_d7_retention() -> dict:
    """Cohort D7 retention over users first seen 7-60 days ago.

    A user is *retained* if they have any event strictly after their first day
    and within 7 days of their first event — i.e. they came back during the
    first week. Users first seen <7d ago are excluded (no full window yet).
    """
    lookback = _cutoff(60)
    rows = execute_db(
        f"SELECT user_id, created_at FROM metric_events "
        f"WHERE user_id IS NOT NULL AND created_at >= {ph()}",
        (lookback,),
        fetch="all",
    ) or []

    by_user: dict[int, list[datetime]] = {}
    for uid, ts in rows:
        dt = _to_dt(ts)
        if dt is None:
            continue
        by_user.setdefault(uid, []).append(dt)

    now = datetime.now()
    cohort = 0
    retained = 0
    for stamps in by_user.values():
        stamps.sort()
        first = stamps[0]
        if (now - first) < timedelta(days=7):
            continue  # not enough time to have a 7-day window
        cohort += 1
        first_day = first.date()
        if any(
            s.date() != first_day and (s - first) <= timedelta(days=7)
            for s in stamps[1:]
        ):
            retained += 1

    return {
        "cohort": cohort,
        "retained": retained,
        "rate": round(retained / cohort, 4) if cohort else 0.0,
        "definition": "% of users (first seen 7-60d ago) who returned within 7 days",
    }
