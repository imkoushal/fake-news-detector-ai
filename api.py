"""
FastAPI REST API for Fake News Detection — Production Server
Serves both the API endpoints AND the static frontend.

Run locally:  uvicorn api:app --reload
Deploy:       Render / Railway / Fly.io
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# ── Structured logging setup (2.4) ──
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger("fake_news_api")

# P3-3: Shared state lives in routers.app_state so routers can import it
# without circular deps. api.py populates the mutable fields at startup.
import routers.app_state as _state
APP_VERSION = _state.APP_VERSION

from scipy.sparse import hstack  # noqa: E402

# Import canonical preprocessing and feature functions (same as training pipeline)
from utils import clean_text  # noqa: E402
from meta_features import extract_single as compute_meta_features  # noqa: E402
from enhanced_features import detect_fake_news_red_flags  # noqa: E402

try:
    from fastapi import FastAPI, HTTPException, Request, UploadFile, File
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse
    from starlette.concurrency import run_in_threadpool
    from pydantic import BaseModel, ConfigDict
    from typing import Optional, List
    import joblib
    import re
    import httpx
    from datetime import datetime, timedelta
    from contextlib import asynccontextmanager
    from functools import lru_cache
    import bcrypt
    import secrets
    import sqlite3
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
except ImportError as e:
    raise SystemExit(
        "FastAPI is required. Install with: pip install -r requirements.txt"
    ) from e

# ── Lifespan handler (replaces deprecated on_event startup/shutdown) ──
# Forward-references _load_model / _init_auth_db / etc., which are defined
# further down at module scope — resolved at call time, i.e. at startup.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup: validate secrets, load model after the port binds ──
    # M7 FIX: Validate critical secrets at startup — log warnings, don't crash
    missing_keys = [k for k in ("GROQ_API_KEY", "GNEWS_API_KEY") if not os.getenv(k)]
    if missing_keys:
        logger.warning(f"Missing API keys (features will be degraded): {', '.join(missing_keys)}")

    logger.info("Initializing database schemas...")
    _init_auth_db()
    _migrate_google_columns()
    _init_feedback_table()
    _metrics.init_metrics_db()  # §5 growth metrics (never crashes startup)
    try:
        from backend.claims_db import init_seo_claims_db
        init_seo_claims_db()
    except Exception as e:
        logger.warning(f"seo_claims init skipped: {e}")
    try:
        from backend.api_keys import init_api_keys_db
        init_api_keys_db()
    except Exception as e:
        logger.warning(f"api_keys init skipped: {e}")

    logger.info("Server is up — loading ML model in lifespan startup...")
    _load_model()

    # ── Register the Telegram webhook if configured (Phase 9.1) ──
    # Never crash startup on failure (same policy as the M7 secret check).
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    tg_base = os.getenv("PUBLIC_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL", "")
    if tg_token and tg_secret and tg_base:
        try:
            from backend.telegram_bot import set_webhook
            await set_webhook(tg_base, tg_secret)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Telegram webhook registration skipped: {e}")
    elif tg_token:
        logger.info("Telegram token set but PUBLIC_BASE_URL/RENDER_EXTERNAL_URL or secret missing — webhook not auto-registered")

    yield

    # ── Shutdown: H1 — close shared httpx.AsyncClient to prevent leaks ──
    from backend.http_client import close_client
    await close_client()

# ── Production detection (from shared state) ──
IS_PRODUCTION = _state.IS_PRODUCTION

# ── Initialize FastAPI ──
# Finding #1: Disable interactive API docs (Swagger/ReDoc/OpenAPI schema) in
# production so the full attack surface isn't handed to anonymous callers.
# They stay enabled locally for development convenience.
_docs_kwargs = (
    {"docs_url": None, "redoc_url": None, "openapi_url": None}
    if IS_PRODUCTION
    else {}
)
app = FastAPI(
    title="Fake News Detector API",
    description="Hybrid ML-powered fake news detection API",
    version=APP_VERSION,
    lifespan=lifespan,
    **_docs_kwargs,
)

# ── P3-3: Register extracted routers ──
from routers.auth import router as _auth_router, migrate_google_columns as _migrate_google_columns
from routers.admin import router as _admin_router
from routers.claims import router as _claims_router
from routers.history import router as _history_router, init_feedback_table as _init_feedback_table
from routers.telegram import router as _telegram_router
from routers.verify import router as _verify_router, _extract_urls_from_text, _check_source_credibility
from routers.analyze import router as _analyze_router, _run_smart_verify
app.include_router(_auth_router)
app.include_router(_admin_router)
app.include_router(_claims_router)
app.include_router(_history_router)
app.include_router(_telegram_router)
app.include_router(_verify_router)
app.include_router(_analyze_router)

# ── CORS — read allowed origins from env, default to localhost for dev ──
_cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8501,http://localhost:5173,http://localhost:5174")
ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(",") if o.strip()]
# In production, add the actual Render domain instead of wildcard
if os.getenv("RENDER"):
    ALLOWED_ORIGINS.append("https://fake-news-detector-8djq.onrender.com")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(
    key_func=lambda request: (
        # Per-user rate limiting: use IP address as the key (safe, not spoofable)
        get_remote_address(request)
    )
)
app.state.limiter = limiter

# ── Custom structured JSON rate-limit handler (Codex Fix #4) ──
async def _custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Return a clean JSON payload instead of the default plain-text error."""
    logger.warning(f"Rate limit exceeded for {request.url.path} — {exc.detail}")
    return JSONResponse(
        status_code=429,
        content={
            "status": "error",
            "message": "Too many requests. Please slow down.",
            "detail": str(exc.detail),
            "retry_after": "see Retry-After header"
        },
        headers={"Retry-After": "60"}
    )
app.add_exception_handler(RateLimitExceeded, _custom_rate_limit_handler)

# Register SlowAPI middleware so rate limits are actually enforced
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)

# ── Phase 5: Request ID middleware for log correlation ──
import uuid as _uuid
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(_uuid.uuid4())[:8])
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# ── Finding #6: Security headers ──
# These are safe to apply globally — they harden the browser without
# restricting which scripts/styles/images the SPA may load, so the frontend
# and Google Sign-In keep working. A full `default-src 'self'` CSP is
# intentionally NOT set here because it would block the existing inline/CDN
# assets; the CSP below only restricts framing, plugins, and <base> hijacking
# (clickjacking + injection protection) without breaking resource loading.
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    # X-XSS-Protection: modern guidance is to disable the legacy auditor (0).
    response.headers.setdefault("X-XSS-Protection", "0")
    response.headers.setdefault(
        "Content-Security-Policy",
        "frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
    )
    # HSTS only in production (over HTTPS) — never force it on local http dev.
    if IS_PRODUCTION:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response

# ── Phase 5: Global exception handler (no raw tracebacks to client) ──
# FIX: Re-raise HTTPException and RateLimitExceeded so FastAPI's built-in
# handlers process them correctly (returns proper 401/404/429 instead of 500).
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, RateLimitExceeded):
        raise exc
    req_id = getattr(request.state, 'request_id', 'unknown')
    logger.error(f"Unhandled exception [{req_id}]: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": req_id}
    )

# ── Database Layer (imported from backend/db.py) ──
from backend.db import get_db, ph, execute_db, init_auth_db, USE_POSTGRES, BASE_DIR
_init_auth_db = init_auth_db  # Keep the old name for startup event

# ── Growth metrics (§5) — activation / retention / viral / cost ──
from backend import metrics as _metrics

# ── Thread-safe Claim Cache (from shared state) ──
claim_cache = _state.claim_cache

# ── Auth Helpers (only what's still needed by remaining api.py routes) ──
from backend.auth import (
    sanitize_preview as _sanitize_preview,
    get_user_from_token as _get_user_from_token,
)


# ── Auth routes extracted to routers/auth.py (P3-3) ──
# Lockout helpers, Pydantic models (SignupRequest, LoginRequest,
# GoogleAuthRequest), and all /api/v1/auth/* endpoints are now served
# by the auth router registered above.

# ── Pydantic Models (used by analysis endpoints still in api.py) ──
class Article(BaseModel):
    text: str
    source: Optional[str] = None
    # None → fall back to the threshold learned on the validation set (config.json).
    # An explicit value (0.0 lenient – 1.0 strict) overrides it per-request.
    sensitivity: Optional[float] = None

    @property
    def safe_text(self) -> str:
        """H6 FIX: Cap text at 50,000 chars to prevent CPU/memory DoS via TF-IDF."""
        return self.text[:50000]

class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    confidence_tier: str
    real_probability: float
    fake_probability: float
    red_flag_score: float
    input_quality: str = "sufficient"
    fake_indicator_words: List[str] = []
    real_indicator_words: List[str] = []
    category: Optional[str] = None
    timestamp: str
    model_version: str = APP_VERSION

class BatchArticle(BaseModel):
    id: str
    text: str

    @property
    def safe_text(self) -> str:
        """H6 FIX: Cap text at 50,000 chars to prevent CPU/memory DoS via TF-IDF."""
        return self.text[:50000]

class BatchRequest(BaseModel):
    articles: List[BatchArticle]

# ── ML Model Loading (deferred to startup event for fast port binding) ──
# All model globals live in routers.app_state so routers can read them.
MODEL_DIR = _state.MODEL_DIR
MODEL_VERSION = _state.MODEL_VERSION
MODEL_METRICS = _state.MODEL_METRICS
MODEL_LOADED = _state.MODEL_LOADED
MODEL_THRESHOLD = _state.MODEL_THRESHOLD
model = _state.model
tfidf = _state.tfidf
scaler = _state.scaler
ood_detector_instance = _state.ood_detector_instance

def _load_model():
    """Load ML model artifacts. Called during FastAPI startup event.
    Writes to both module-level aliases AND routers.app_state so routers
    can read the loaded state."""
    global model, tfidf, scaler, MODEL_LOADED, MODEL_VERSION, MODEL_METRICS, MODEL_THRESHOLD, ood_detector_instance
    try:
        model = _state.model = joblib.load(MODEL_DIR / "model.joblib")
        tfidf = _state.tfidf = joblib.load(MODEL_DIR / "tfidf.joblib")
        scaler = _state.scaler = joblib.load(MODEL_DIR / "scaler.joblib")
        MODEL_LOADED = _state.MODEL_LOADED = True
        model_type_name = "VERIFAI_ENSEMBLE"
        # Load version & metrics from config.json if present
        cfg_path = MODEL_DIR / "config.json"
        if cfg_path.exists():
            import json as _json
            with open(cfg_path) as f:
                cfg = _json.load(f)
            MODEL_VERSION = _state.MODEL_VERSION = cfg.get("version", MODEL_VERSION)
            MODEL_THRESHOLD = _state.MODEL_THRESHOLD = float(cfg.get("threshold", MODEL_THRESHOLD))
            model_type_name = cfg.get("model_type", model_type_name)
            MODEL_METRICS = _state.MODEL_METRICS = {
                "accuracy": cfg.get("accuracy"),
                "f1_score": cfg.get("f1_score"),
                "roc_auc": cfg.get("roc_auc"),
                "training_date": cfg.get("training_date"),
                "total_features": cfg.get("total_features"),
                "model_type": model_type_name,
                "total_training_samples": cfg.get("total_training_samples"),
            }
        logger.info(f"Model '{model_type_name}' v{MODEL_VERSION} loaded successfully!")

        # Phase 5: Load OOD detector for confidence calibration
        import numpy as np
        ood_centroid_path = MODEL_DIR / "ood_centroid.npy"
        if ood_centroid_path.exists():
            from ood_detector import OODDetector
            centroid = np.load(ood_centroid_path)
            ood_detector_instance = _state.ood_detector_instance = OODDetector(tfidf, centroid)
            logger.info(f"OOD detector loaded (centroid: {centroid.shape[0]} dims)")
        else:
            logger.warning("OOD centroid not found — OOD detection disabled")
    except Exception as e:
        MODEL_LOADED = _state.MODEL_LOADED = False
        logger.warning(f"Model could not be loaded: {e}")

# ── Analysis, RAG & Verification routes extracted to routers/analyze.py (P3-3) ──
# All /api/v1/analyze, /api/v1/smart-verify, /api/v1/transcribe, /api/v1/batch, etc.
# are now served by the analyze router.


# ── All router endpoints extracted to routers/ (P3-3) ──
# auth, admin, claims, history, telegram, verify, analyze routers are registered above.



# ── Phase 11.2: SEO — Structured Data ──
# NOTE: /sitemap.xml and /robots.txt are defined earlier (Phase 11.2 SEO
# Infrastructure block). Duplicate definitions previously here were shadowed
# (Starlette matches the first-registered route) and have been removed.

# NOTE: Duplicate /ld-json endpoint removed — use /jsonld instead (defined earlier).

# ── API catch-all: return proper 404 for unmatched /api/ paths ──
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def api_catchall(path: str):
    raise HTTPException(404, f"API endpoint /api/{path} not found")

# ── Serve Static SPA Frontend ──
FRONTEND_DIR = BASE_DIR / "landing-page" / "dist"

if FRONTEND_DIR.exists():
    logger.info(f"SPA frontend found at {FRONTEND_DIR}")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Serve actual files from dist (JS, CSS, images, etc.)
        if full_path:
            base = FRONTEND_DIR.resolve()
            try:
                file_path = (FRONTEND_DIR / full_path).resolve()
            except (ValueError, OSError):
                raise HTTPException(400, "Invalid path")
            # M3 FIX: Prevent path traversal. is_relative_to avoids the
            # `startswith` sibling-prefix bypass (e.g. .../dist-secret/x
            # would pass a str prefix check against .../dist).
            if not file_path.is_relative_to(base):
                raise HTTPException(403, "Forbidden")
            if file_path.is_file():
                return FileResponse(str(file_path))
        # Everything else → index.html (React Router handles client-side routing)
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    logger.warning(f"SPA frontend NOT found at {FRONTEND_DIR}")

    @app.get("/")
    async def serve_index():
        return {"message": "Fake News Detector API (React Frontend Not Built)", "docs": "/docs"}

# ── Entry Point ──
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

