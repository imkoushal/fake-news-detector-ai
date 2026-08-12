"""
Admin router — /info, /health, /admin/stats, /admin/metrics.
Extracted from api.py as part of P3-3 router split.
"""
import os
import logging
import secrets
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from backend.db import get_db, ph, execute_db, USE_POSTGRES
from backend import metrics as _metrics
import routers.app_state as _state

logger = logging.getLogger("fake_news_api")

router = APIRouter(tags=["Admin"])


@router.get("/api/v1/info")
async def api_info():
    return {
        "name": "Fake News Detector API",
        "version": _state.MODEL_VERSION,
        "status": "operational" if _state.MODEL_LOADED else "model_not_loaded",
        "metrics": _state.MODEL_METRICS
    }


@router.get("/health")
async def health_check(request: Request):
    """Phase 5: Tiered health check — model, DB, and cache status.

    Finding #5: the detailed payload (db engine, model version, cache config,
    which API keys are set) is only returned to internal callers — non-prod, or
    a request carrying the HEALTH_DETAIL_TOKEN. Public callers get a minimal
    liveness response so recon can't fingerprint the stack. Always HTTP 200 so
    platform health checks (Render) still pass.
    """
    _detail_token = os.getenv("HEALTH_DETAIL_TOKEN", "")
    _provided = (
        request.headers.get("X-Health-Token", "")
        or request.query_params.get("token", "")
    )
    _show_detail = (not _state.IS_PRODUCTION) or (
        bool(_detail_token) and secrets.compare_digest(_provided, _detail_token)
    )
    if not _show_detail:
        return {"status": "ok" if _state.MODEL_LOADED else "degraded"}

    # Tier 1: Basic server up
    health = {
        "status": "healthy",
        "model_loaded": _state.MODEL_LOADED,
        "model_version": _state.MODEL_VERSION,
        "db_mode": "postgresql" if USE_POSTGRES else "sqlite",
        "timestamp": datetime.now().isoformat(),
    }

    # Tier 2: DB connectivity
    try:
        execute_db("SELECT 1", fetch="one")
        health["db_connected"] = True
    except Exception:
        health["db_connected"] = False
        health["status"] = "degraded"

    # Tier 3: Cache stats
    health["cache"] = _state.claim_cache.stats()

    # Tier 4: External API key presence
    health["external_apis"] = {
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "gnews": bool(os.getenv("GNEWS_API_KEY")),
        "google_factcheck": bool(os.getenv("GOOGLE_FACTCHECK_API_KEY")),
    }

    if not _state.MODEL_LOADED:
        health["status"] = "unhealthy"

    return health


@router.get("/api/v1/admin/stats")
async def admin_stats(request: Request):
    """Protected admin endpoint — returns global platform stats."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not _state.ADMIN_SECRET or not secrets.compare_digest(token, _state.ADMIN_SECRET):
        raise HTTPException(403, "Admin access required")

    conn = get_db()
    c = conn.cursor()
    try:
        # Global analysis totals
        c.execute("SELECT COUNT(*), COALESCE(AVG(confidence),0) FROM analyses")
        total_analyses, avg_conf = c.fetchone()

        c.execute("SELECT COUNT(*) FROM analyses WHERE prediction='FAKE'")
        total_fake = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM feedback")
        total_feedback = c.fetchone()[0]

        # Daily trend (last 14 days)
        if USE_POSTGRES:
            c.execute("""SELECT DATE(created_at) as d, prediction, COUNT(*) FROM analyses
                WHERE created_at >= CURRENT_DATE - INTERVAL '13 days'
                GROUP BY d, prediction ORDER BY d""")
        else:
            c.execute("""SELECT DATE(created_at) as d, prediction, COUNT(*) FROM analyses
                WHERE created_at >= DATE('now', '-13 days')
                GROUP BY d, prediction ORDER BY d""")
        trend_raw = c.fetchall()
        trend = {}
        for row in trend_raw:
            day = str(row[0])
            if day not in trend:
                trend[day] = {"real": 0, "fake": 0}
            trend[day][row[1].lower()] = row[2]

        # Recent feedback (last 20)
        c.execute("""SELECT model_prediction, user_correction, text_preview, created_at
            FROM feedback ORDER BY created_at DESC LIMIT 20""")
        recent_feedback = [
            {"model": r[0], "user": r[1], "preview": r[2][:80], "date": str(r[3])}
            for r in c.fetchall()
        ]

        return {
            "total_analyses": total_analyses,
            "total_fake": total_fake,
            "total_real": total_analyses - total_fake,
            "avg_confidence": round(float(avg_conf), 1),
            "total_users": total_users,
            "total_feedback": total_feedback,
            "model_version": _state.MODEL_VERSION,
            "model_metrics": _state.MODEL_METRICS,
            "daily_trend": trend,
            "recent_feedback": recent_feedback,
            "generated_at": datetime.now().isoformat()
        }
    finally:
        conn.close()


@router.get("/api/v1/admin/metrics")
async def admin_metrics(request: Request, window_days: int = 30):
    """Protected admin endpoint — §5 growth metrics (activation, D7
    retention, viral coefficient, cost-per-check) over a trailing window."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not _state.ADMIN_SECRET or not secrets.compare_digest(token, _state.ADMIN_SECRET):
        raise HTTPException(403, "Admin access required")
    window_days = max(1, min(int(window_days), 365))
    return _metrics.compute_metrics(window_days=window_days)
