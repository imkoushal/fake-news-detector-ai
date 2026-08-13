"""
History, User Stats, Feedback & Share router.
Extracted from api.py as part of P3-3 router split.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from backend.db import get_db, ph, USE_POSTGRES
from backend.auth import get_user_from_token as _get_user_from_token, sanitize_preview as _sanitize_preview
from backend import metrics as _metrics

logger = logging.getLogger("fake_news_api")

router = APIRouter(tags=["History & User"])


# ── Pydantic Models ──
class FeedbackRequest(BaseModel):
    text: str
    model_prediction: str
    user_correction: str
    reason: Optional[str] = None


class ShareRequest(BaseModel):
    channel: Optional[str] = None  # e.g. "whatsapp", "twitter", "copy"


def init_feedback_table():
    """Create feedback table if it doesn't exist."""
    conn = get_db()
    c = conn.cursor()
    try:
        if USE_POSTGRES:
            c.execute('''CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                text_preview TEXT NOT NULL,
                model_prediction TEXT NOT NULL,
                user_correction TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        else:
            c.execute('''CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text_preview TEXT NOT NULL,
                model_prediction TEXT NOT NULL,
                user_correction TEXT NOT NULL,
                reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')
        conn.commit()
    finally:
        conn.close()


# ── Endpoints ──

@router.get("/api/v1/user/stats")
async def get_user_stats(request: Request):
    """Get dashboard stats for the authenticated user."""
    user_id = await run_in_threadpool(_get_user_from_token, request)
    if not user_id:
        raise HTTPException(401, "Not authenticated")

    def _fetch_stats_sync():
        conn = get_db()
        c = conn.cursor()
        try:
            # Total analyses
            c.execute(f"SELECT COUNT(*) FROM analyses WHERE user_id = {ph()}", (user_id,))
            total = c.fetchone()[0]
            # Avg confidence
            c.execute(f"SELECT COALESCE(AVG(confidence), 0) FROM analyses WHERE user_id = {ph()}", (user_id,))
            avg_conf = round(c.fetchone()[0], 1)
            # Fake count
            c.execute(f"SELECT COUNT(*) FROM analyses WHERE user_id = {ph()} AND prediction = 'FAKE'", (user_id,))
            fake_count = c.fetchone()[0]
            # Real count
            real_count = total - fake_count
            # Recent 10 analyses
            c.execute(f"SELECT text_preview, prediction, confidence, red_flag_score, created_at FROM analyses WHERE user_id = {ph()} ORDER BY created_at DESC LIMIT 10", (user_id,))
            recent = []
            for row in c.fetchall():
                recent.append({
                    "preview": row[0], "prediction": row[1],
                    "confidence": round(row[2], 1), "red_flags": round(row[3] * 100),
                    "date": str(row[4])
                })
            # Daily trend (last 7 days)
            if USE_POSTGRES:
                c.execute(f"""SELECT DATE(created_at) as d, prediction, COUNT(*) FROM analyses
                    WHERE user_id = {ph()} AND created_at >= CURRENT_DATE - INTERVAL '6 days'
                    GROUP BY d, prediction ORDER BY d""", (user_id,))
            else:
                c.execute(f"""SELECT DATE(created_at) as d, prediction, COUNT(*) FROM analyses
                    WHERE user_id = {ph()} AND created_at >= DATE('now', '-6 days')
                    GROUP BY d, prediction ORDER BY d""", (user_id,))
            trend_raw = c.fetchall()
            trend = {}
            for row in trend_raw:
                day = str(row[0])
                if day not in trend:
                    trend[day] = {"real": 0, "fake": 0}
                trend[day][row[1].lower()] = row[2]
            # Global stats (all users combined)
            c.execute("SELECT COUNT(*) FROM analyses")
            global_total = c.fetchone()[0]
            c.execute("SELECT COALESCE(AVG(confidence), 0) FROM analyses")
            global_avg_conf = round(c.fetchone()[0], 1)
            c.execute("SELECT COUNT(*) FROM analyses WHERE prediction = 'FAKE'")
            global_fake = c.fetchone()[0]

            return {
                "total": total, "avg_confidence": avg_conf,
                "fake_count": fake_count, "real_count": real_count,
                "recent": recent, "trend": trend,
                "global_total": global_total, "global_avg_confidence": global_avg_conf,
                "global_fake_count": global_fake, "global_real_count": global_total - global_fake
            }
        finally:
            conn.close()

    return await run_in_threadpool(_fetch_stats_sync)


@router.get("/api/v1/user/history")
async def get_user_history(request: Request, page: int = 1, limit: int = 25, filter: str = "all"):
    """Get paginated analysis history for the authenticated user."""
    user_id = await run_in_threadpool(_get_user_from_token, request)
    if not user_id:
        raise HTTPException(401, "Not authenticated")

    def _fetch_history_sync():
        conn = get_db()
        c = conn.cursor()
        try:
            where = f"user_id = {ph()}"
            params = [user_id]
            if filter == "real":
                where += f" AND prediction = {ph()}"
                params.append("REAL")
            elif filter == "fake":
                where += f" AND prediction = {ph()}"
                params.append("FAKE")
            # Count
            c.execute(f"SELECT COUNT(*) FROM analyses WHERE {where}", tuple(params))
            total_count = c.fetchone()[0]
            # Paginated results
            offset = (page - 1) * limit
            c.execute(f"SELECT id, text_preview, prediction, confidence, real_prob, fake_prob, red_flag_score, created_at FROM analyses WHERE {where} ORDER BY created_at DESC LIMIT {ph()} OFFSET {ph()}", tuple(params + [limit, offset]))
            rows = []
            for row in c.fetchall():
                rows.append({
                    "id": row[0], "preview": row[1], "prediction": row[2],
                    "confidence": round(row[3], 1), "real_prob": round(row[4], 3),
                    "fake_prob": round(row[5], 3), "red_flags": round(row[6] * 100),
                    "date": str(row[7])
                })
            return {
                "items": rows, "total": total_count,
                "page": page, "limit": limit, "pages": max(1, -(-total_count // limit))
            }
        finally:
            conn.close()

    return await run_in_threadpool(_fetch_history_sync)


@router.post("/api/v1/feedback")
async def submit_feedback(req: FeedbackRequest, request: Request):
    """Accept user correction on a model prediction for future retraining."""
    if req.model_prediction not in ("REAL", "FAKE") or req.user_correction not in ("REAL", "FAKE"):
        raise HTTPException(400, "model_prediction and user_correction must be REAL or FAKE")
    if len(req.text.strip()) < 20:
        raise HTTPException(400, "Text too short")

    user_id = _get_user_from_token(request)
    preview = _sanitize_preview(req.text.strip(), max_len=300)
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            f"INSERT INTO feedback (user_id, text_preview, model_prediction, user_correction, reason) VALUES ({ph(5)})",
            (user_id, preview, req.model_prediction, req.user_correction, req.reason)
        )
        conn.commit()
        logger.info(f"Feedback received: model={req.model_prediction} -> user={req.user_correction}")
        return {"ok": True, "message": "Feedback recorded. Thank you!"}
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save feedback: {e}")
        raise HTTPException(500, "Failed to save feedback")
    finally:
        conn.close()


@router.post("/api/v1/share")
async def log_share(req: ShareRequest, request: Request):
    """Record a share action for the viral-coefficient metric."""
    channel = (req.channel or "unknown").strip().lower()[:32]
    _metrics.log_event(
        _metrics.EVENT_SHARE,
        user_id=_get_user_from_token(request),
        source="web",
        meta={"channel": channel},
    )
    return {"ok": True}
