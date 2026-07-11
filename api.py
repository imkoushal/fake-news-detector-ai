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

# Single source of truth for the application version (keep in sync with README).
APP_VERSION = "8.0"

from scipy.sparse import hstack  # noqa: E402

# Import canonical preprocessing and feature functions (same as training pipeline)
from utils import clean_text  # noqa: E402
from meta_features import extract_single as compute_meta_features  # noqa: E402
from enhanced_features import detect_fake_news_red_flags  # noqa: E402

try:
    from fastapi import FastAPI, HTTPException, Request, UploadFile, File
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel, ConfigDict
    from typing import Optional, List
    import joblib
    import re
    import requests
    import httpx
    from datetime import datetime, timedelta
    from contextlib import asynccontextmanager
    import bcrypt
    import secrets
    import sqlite3
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("FastAPI not installed. Install with: pip install fastapi uvicorn slowapi pydantic")

if not FASTAPI_AVAILABLE:
    class DummyApp:
        pass
    app = DummyApp()
else:
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

    # ── Production detection ──
    # Render sets RENDER=true automatically; APP_ENV=production is an explicit
    # override (matches the existing convention in .env.example).
    IS_PRODUCTION = os.getenv("APP_ENV", "").lower() in ("production", "prod") or bool(os.getenv("RENDER"))

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
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
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

    # ── Thread-safe Claim Cache (imported from backend/cache.py) ──
    from backend.cache import ClaimCache
    claim_cache = ClaimCache(max_size=500, ttl_seconds=3600)
    logger.info("Claim cache initialized (max=500, TTL=1h)")

    # ── Auth Helpers (imported from backend/auth.py) ──
    from backend.auth import (
        hash_password as _hash_password,
        verify_password as _verify_password,
        sanitize_preview as _sanitize_preview,
        get_user_from_token as _get_user_from_token,
        create_session as _create_session,
        SESSION_TTL_DAYS,
    )

    # ── Finding #3: Login brute-force lockout ──
    # Per-email failed-attempt tracker. Complements the IP-based slowapi limit:
    # slowapi caps request *rate*, this locks a targeted *account* after repeated
    # failures regardless of how the attacker rotates IPs.
    # NOTE: in-memory + per-process. Fine for the current single-instance Render
    # deployment (resets on restart); move to Redis/DB if scaled horizontally.
    from collections import defaultdict as _defaultdict
    _failed_logins: dict = _defaultdict(list)  # email -> [unix_ts, ...]
    LOGIN_MAX_FAILURES = 5      # failures within the window before lockout
    LOGIN_FAIL_WINDOW = 900     # 15 min sliding window (seconds)
    LOGIN_LOCKOUT_SECS = 900    # lock duration after threshold reached

    def _login_locked(email: str) -> bool:
        """True if this email is currently locked out; prunes stale entries."""
        now = datetime.now().timestamp()
        recent = [t for t in _failed_logins.get(email, []) if now - t < LOGIN_LOCKOUT_SECS]
        _failed_logins[email] = recent
        return len(recent) >= LOGIN_MAX_FAILURES

    def _record_login_failure(email: str) -> None:
        now = datetime.now().timestamp()
        recent = [t for t in _failed_logins.get(email, []) if now - t < LOGIN_FAIL_WINDOW]
        recent.append(now)
        _failed_logins[email] = recent

    def _clear_login_failures(email: str) -> None:
        _failed_logins.pop(email, None)

    # ── Pydantic Models ──
    class SignupRequest(BaseModel):
        # Finding #4 hardening: reject unknown fields (e.g. an injected `role`)
        # with 422 instead of silently ignoring them. Privilege columns are never
        # bound from the request body regardless — this just makes intent explicit.
        model_config = ConfigDict(extra="forbid")
        name: str
        email: str
        password: str

    class LoginRequest(BaseModel):
        model_config = ConfigDict(extra="forbid")
        email: str
        password: str

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

    # ── Auth Endpoints ──
    @app.post("/api/v1/auth/signup")
    @limiter.limit("10/minute")
    async def signup(req: SignupRequest, request: Request):
        if len(req.password) < 6:
            raise HTTPException(400, "Password must be at least 6 characters")
        if len(req.name.strip()) < 1:
            raise HTTPException(400, "Name is required")

        salt = "bcrypt"  # Marker — bcrypt embeds its own salt in the hash
        pw_hash = _hash_password(req.password)

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                f"INSERT INTO users (name, email, password_hash, salt) VALUES ({ph(4)})",
                (req.name.strip(), req.email.strip().lower(), pw_hash, salt)
            )
            if USE_POSTGRES:
                c.execute("SELECT currval(pg_get_serial_sequence('users','id'))")
                user_id = c.fetchone()[0]
            else:
                user_id = c.lastrowid
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now() + timedelta(days=SESSION_TTL_DAYS)).isoformat()
            c.execute(f"INSERT INTO sessions (token, user_id, expires_at) VALUES ({ph(3)})", (token, user_id, expires_at))
            conn.commit()
            _metrics.log_event(_metrics.EVENT_SIGNUP, user_id=user_id, source="web", meta={"method": "password"})
            return {
                "token": token,
                "user": {"id": user_id, "name": req.name.strip(), "email": req.email.strip().lower()}
            }
        except Exception as e:
            conn.rollback()
            err = str(e).lower()
            if "unique" in err or "duplicate" in err:
                raise HTTPException(409, "An account with this email already exists")
            logger.error(f"Signup error: {e}")
            raise HTTPException(500, "Account creation failed. Please try again.")
        finally:
            conn.close()

    @app.post("/api/v1/auth/login")
    @limiter.limit("5/minute")
    async def login(req: LoginRequest, request: Request):
        email_key = req.email.strip().lower()
        # Finding #3: account lockout after repeated failures for this email.
        if _login_locked(email_key):
            logger.warning(f"Login blocked — account locked out: {email_key}")
            raise HTTPException(
                429,
                "Too many failed login attempts. Try again in 15 minutes.",
            )
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                f"SELECT id, name, email, password_hash, salt FROM users WHERE email = {ph()}",
                (email_key,)
            )
            user = c.fetchone()
            if not user:
                # M5 FIX: Dummy bcrypt hash to prevent timing-based user enumeration
                _hash_password("dummy-password-for-constant-time")
                _record_login_failure(email_key)
                raise HTTPException(401, "Invalid email or password")
            if not _verify_password(req.password, user[3], user[4]):
                _record_login_failure(email_key)
                raise HTTPException(401, "Invalid email or password")

            # Successful auth — clear the failure counter for this account.
            _clear_login_failures(email_key)

            # Auto-upgrade legacy SHA-256 hashes to bcrypt on successful login
            # Commit upgrade immediately so it persists even if session creation fails
            if user[4] != "bcrypt" and not user[3].startswith("$2b$"):
                logger.warning(f"Legacy SHA-256 hash detected for user {user[0]} — auto-upgrading to bcrypt. Consider prompting this user to change their password.")
                new_hash = _hash_password(req.password)
                c.execute(
                    f"UPDATE users SET password_hash = {ph()}, salt = {ph()} WHERE id = {ph()}",
                    (new_hash, "bcrypt", user[0])
                )
                conn.commit()  # Commit hash upgrade independently
                logger.info(f"Auto-upgraded password hash to bcrypt for user {user[0]}")

            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now() + timedelta(days=SESSION_TTL_DAYS)).isoformat()
            c.execute(f"INSERT INTO sessions (token, user_id, expires_at) VALUES ({ph(3)})", (token, user[0], expires_at))
            conn.commit()
            return {"token": token, "user": {"id": user[0], "name": user[1], "email": user[2]}}
        finally:
            conn.close()

    @app.get("/api/v1/auth/me")
    async def get_me(request: Request):
        # Resolve via the shared helper so expiry is enforced (and expired
        # sessions are purged) — consistent with every other authed endpoint.
        user_id = _get_user_from_token(request)
        if not user_id:
            raise HTTPException(401, "Invalid session")
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                f"SELECT id, name, email, avatar_url FROM users WHERE id = {ph()}",
                (user_id,)
            )
            user = c.fetchone()
            if not user:
                raise HTTPException(401, "Invalid session")
            return {"id": user[0], "name": user[1], "email": user[2], "avatar_url": user[3] or ""}
        finally:
            conn.close()

    @app.post("/api/v1/auth/logout")
    async def logout(request: Request):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token:
            # Codex Fix #3: Wrap in try/finally to prevent connection leak on error
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute(f"DELETE FROM sessions WHERE token = {ph()}", (token,))
                conn.commit()
            except Exception as e:
                logger.error(f"Logout session cleanup failed: {e}")
                conn.rollback()
            finally:
                conn.close()
        return {"ok": True}

    # ── Google OAuth ──
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

    # Migration: add google_id and avatar_url columns if missing
    def _migrate_google_columns():
        try:
            _conn = get_db()
            _c = _conn.cursor()
            try:
                _c.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
                logger.info("Migrated users table: added google_id column")
            except Exception:
                pass
            try:
                _c.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
                logger.info("Migrated users table: added avatar_url column")
            except Exception:
                pass
            _conn.commit()
            _conn.close()
        except Exception as e:
            logger.warning(f"Google auth migration skipped: {e}")

    class GoogleAuthRequest(BaseModel):
        credential: str  # The ID token from Google Identity Services

    @app.post("/api/v1/auth/google")
    @limiter.limit("20/minute")
    async def google_auth(req: GoogleAuthRequest, request: Request):
        """Authenticate via Google Sign-In.
        C1 FIX: Verifies JWT signature cryptographically using google-auth library.
        """
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(500, "Google OAuth is not configured on this server")

        # C1 FIX: Cryptographic JWT verification (replaces insecure base64 decode)
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests
            payload = google_id_token.verify_oauth2_token(
                req.credential,
                google_requests.Request(),
                GOOGLE_CLIENT_ID
            )
        except ImportError:
            # Fallback if google-auth not installed — decode + verify claims manually
            logger.warning("google-auth not installed, falling back to manual JWT decode")
            import json as _json
            import base64
            try:
                parts = req.credential.split(".")
                if len(parts) != 3:
                    raise ValueError("Invalid JWT format")
                payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
                payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
            except Exception as e:
                logger.error(f"Google token decode failed: {e}")
                raise HTTPException(401, "Invalid Google credential")

            # Verify essential claims
            if payload.get("aud") != GOOGLE_CLIENT_ID:
                raise HTTPException(401, "Token audience mismatch")
            if payload.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
                raise HTTPException(401, "Token issuer invalid")
            import time as _time
            if payload.get("exp", 0) < _time.time():
                raise HTTPException(401, "Google token has expired")
        except ValueError as e:
            logger.error(f"Google token verification failed: {e}")
            raise HTTPException(401, "Invalid Google credential")

        google_id = payload.get("sub")
        email = payload.get("email", "").lower()
        name = payload.get("name", email.split("@")[0])
        avatar_url = payload.get("picture", "")

        if not email or not google_id:
            raise HTTPException(401, "Google token missing required fields")

        conn = get_db()
        c = conn.cursor()
        try:
            # Check if user exists by google_id or email
            c.execute(f"SELECT id, name, email, avatar_url FROM users WHERE email = {ph()}", (email,))
            user = c.fetchone()
            is_new_user = user is None

            if user:
                # Existing user — update google_id and avatar if not set
                user_id, user_name, user_email = user[0], user[1], user[2]
                c.execute(
                    f"UPDATE users SET google_id = {ph()}, avatar_url = {ph()} WHERE id = {ph()}",
                    (google_id, avatar_url, user_id)
                )
            else:
                # New user — create account with a random password (they'll only use Google login)
                random_pw_hash = _hash_password(secrets.token_urlsafe(32))
                c.execute(
                    f"INSERT INTO users (name, email, password_hash, salt, google_id, avatar_url) VALUES ({ph(6)})",
                    (name, email, random_pw_hash, "bcrypt", google_id, avatar_url)
                )
                if USE_POSTGRES:
                    c.execute("SELECT currval(pg_get_serial_sequence('users','id'))")
                    user_id = c.fetchone()[0]
                else:
                    user_id = c.lastrowid
                user_name = name
                user_email = email

            # Create session
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now() + timedelta(days=SESSION_TTL_DAYS)).isoformat()
            c.execute(f"INSERT INTO sessions (token, user_id, expires_at) VALUES ({ph(3)})", (token, user_id, expires_at))
            conn.commit()
            if is_new_user:
                _metrics.log_event(_metrics.EVENT_SIGNUP, user_id=user_id, source="web", meta={"method": "google"})

            return {
                "token": token,
                "user": {
                    "id": user_id,
                    "name": user_name,
                    "email": user_email,
                    "avatar_url": avatar_url
                }
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Google auth failed: {e}")
            raise HTTPException(500, "Google authentication failed")
        finally:
            conn.close()
    # Expose Google Client ID to frontend (never expose the secret, only the public client ID)
    @app.get("/api/v1/auth/google-client-id")
    async def get_google_client_id():
        return {"client_id": GOOGLE_CLIENT_ID}

    # ── ML Model Loading (deferred to startup event for fast port binding) ──
    MODEL_DIR = BASE_DIR / "models"
    MODEL_VERSION = APP_VERSION  # fallback
    MODEL_METRICS = {}
    MODEL_LOADED = False
    # Decision threshold learned on the validation set during training (config.json).
    # Falls back to 0.5 only if the model config is unavailable.
    MODEL_THRESHOLD = 0.5
    model = None
    tfidf = None
    scaler = None

    def _load_model():
        """Load ML model artifacts. Called during FastAPI startup event."""
        global model, tfidf, scaler, MODEL_LOADED, MODEL_VERSION, MODEL_METRICS, MODEL_THRESHOLD
        try:
            model = joblib.load(MODEL_DIR / "model.joblib")
            tfidf = joblib.load(MODEL_DIR / "tfidf.joblib")
            scaler = joblib.load(MODEL_DIR / "scaler.joblib")
            MODEL_LOADED = True
            model_type_name = "VERIFAI_ENSEMBLE"
            # Load version & metrics from config.json if present
            cfg_path = MODEL_DIR / "config.json"
            if cfg_path.exists():
                import json as _json
                with open(cfg_path) as f:
                    cfg = _json.load(f)
                MODEL_VERSION = cfg.get("version", MODEL_VERSION)
                MODEL_THRESHOLD = float(cfg.get("threshold", MODEL_THRESHOLD))
                model_type_name = cfg.get("model_type", model_type_name)
                MODEL_METRICS = {
                    "accuracy": cfg.get("accuracy"),
                    "f1_score": cfg.get("f1_score"),
                    "roc_auc": cfg.get("roc_auc"),
                    "training_date": cfg.get("training_date"),
                    "total_features": cfg.get("total_features"),
                    "model_type": model_type_name,
                    "total_training_samples": cfg.get("total_training_samples"),
                }
            logger.info(f"Model '{model_type_name}' v{MODEL_VERSION} loaded successfully!")
        except Exception as e:
            MODEL_LOADED = False
            logger.warning(f"Model could not be loaded: {e}")

    # NOTE: model loading, DB init, and httpx shutdown are handled by the
    # `lifespan` context manager defined above (replaces deprecated on_event).

    # ── Word Explainability Helper (3.7) ──
    def _get_top_words(text: str, top_n: int = 6):
        """Return top words pushing toward FAKE and REAL using LR base estimator."""
        try:
            cleaned = clean_text(text)
            feature_names = tfidf.get_feature_names_out()
            tfidf_vec = tfidf.transform([cleaned])

            # Extract LR base estimator from VotingClassifier
            lr_estimator = None
            for name, est in zip(model.estimators, model.estimators_):
                if hasattr(est, 'coef_'):  # LogisticRegression
                    lr_estimator = est
                    break

            if lr_estimator is None:
                return [], []

            coef = lr_estimator.coef_[0]  # shape: (n_tfidf_features + n_meta,)
            tfidf_coef = coef[:len(feature_names)]  # Only TF-IDF portion

            # Get TF-IDF scores for this document
            doc_tfidf = tfidf_vec.toarray()[0]

            # Weight = coefficient * tfidf_score — tells which words actually influenced this doc
            weights = tfidf_coef * doc_tfidf

            # Non-zero only (words present in doc)
            nonzero = [(feature_names[i], float(weights[i])) for i in range(len(weights)) if doc_tfidf[i] > 0]
            nonzero.sort(key=lambda x: x[1])

            fake_words = [w for w, s in nonzero[:top_n] if s < 0]   # Negative coef = push toward FAKE
            real_words = [w for w, s in reversed(nonzero[-top_n:]) if s > 0]  # Positive = REAL

            return fake_words, real_words
        except Exception as e:
            logger.debug(f"Explainability failed: {e}")
            return [], []

    # ── Helper Functions ──
    # clean_text, compute_meta_features (extract_single), and detect_fake_news_red_flags
    # are now imported from utils.py, meta_features.py, and enhanced_features.py respectively.
    # This ensures the API uses the EXACT same preprocessing as the training pipeline.

    # ── ML API Endpoints ──
    @app.get("/api/v1/info")
    async def api_info():
        return {
            "name": "Fake News Detector API",
            "version": MODEL_VERSION,
            "status": "operational" if MODEL_LOADED else "model_not_loaded",
            "metrics": MODEL_METRICS
        }

    @app.get("/health")
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
        _show_detail = (not IS_PRODUCTION) or (
            bool(_detail_token) and secrets.compare_digest(_provided, _detail_token)
        )
        if not _show_detail:
            return {"status": "ok" if MODEL_LOADED else "degraded"}

        # Tier 1: Basic server up
        health = {
            "status": "healthy",
            "model_loaded": MODEL_LOADED,
            "model_version": MODEL_VERSION,
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
        health["cache"] = claim_cache.stats()

        # Tier 4: External API key presence
        health["external_apis"] = {
            "groq": bool(os.getenv("GROQ_API_KEY")),
            "gnews": bool(os.getenv("GNEWS_API_KEY")),
            "google_factcheck": bool(os.getenv("GOOGLE_FACTCHECK_API_KEY")),
        }

        if not MODEL_LOADED:
            health["status"] = "unhealthy"

        return health

    # Debug endpoint removed — was leaking DB schema unauthenticated (Issue #6)

    @app.post("/api/v1/analyze", response_model=PredictionResponse)
    @limiter.limit("30/minute")
    async def analyze_article(article: Article, request: Request):
        if not MODEL_LOADED:
            raise HTTPException(503, "Model not loaded")

        # H6 FIX: use safe_text (50k cap) to bound TF-IDF/meta CPU & memory.
        text = article.safe_text.strip()
        word_count = len(text.split())

        # Soft validation: reject only truly empty/trivial input
        if len(text) < 10 or word_count < 3:
            raise HTTPException(400, "Please enter at least a few words to analyze.")

        # Determine input quality for confidence adjustment
        if word_count < 10:
            input_quality = "short_claim"
        elif word_count < 30:
            input_quality = "headline"
        else:
            input_quality = "sufficient"

        cleaned = clean_text(text)
        tfidf_features = tfidf.transform([cleaned])

        # ML-4 FIX: Normalize whitespace to match training preprocessing
        text_normalized = re.sub(r'\s+', ' ', text).strip()
        meta = compute_meta_features(text_normalized).reshape(1, -1)
        meta_scaled = scaler.transform(meta)
        features = hstack([tfidf_features, meta_scaled])

        proba = model.predict_proba(features)[0]
        real_prob, fake_prob = float(proba[1]), float(proba[0])
        red_flag_score = detect_fake_news_red_flags(text)
        # Use client-supplied sensitivity as the decision threshold when provided,
        # otherwise fall back to the threshold learned on the validation set (config.json).
        threshold = max(0.0, min(1.0, article.sensitivity if article.sensitivity is not None else MODEL_THRESHOLD))
        prediction = "REAL" if real_prob >= threshold else "FAKE"
        confidence = max(real_prob, fake_prob) * 100

        # Dampen confidence for short inputs — not enough context
        if input_quality == "short_claim":
            confidence = min(confidence, 60.0)
        elif input_quality == "headline":
            confidence = min(confidence, 80.0)

        # Assign confidence tier (incorporates both confidence level AND prediction direction)
        if confidence >= 90:
            confidence_tier = "Verified Real" if prediction == "REAL" else "Confirmed Fake"
        elif confidence >= 75:
            confidence_tier = "Likely Real" if prediction == "REAL" else "Likely Fake"
        elif confidence >= 60:
            confidence_tier = "Slightly Real" if prediction == "REAL" else "Slightly Fake"
        elif confidence >= 50:
            confidence_tier = "Borderline Real" if prediction == "REAL" else "Borderline Fake"
        else:
            confidence_tier = "Borderline Real" if prediction == "REAL" else "Borderline Fake"

        # Save analysis to DB only if input is long enough to be reliable
        # Short claims (< 30 words) produce dampened scores — don't pollute history
        user_id = _get_user_from_token(request)
        # §5 metrics: every analysis is a "check" (ML path — local model, ~$0).
        _metrics.log_event(
            _metrics.EVENT_CHECK, user_id=user_id, source="web", cost_usd=0.0,
            meta={"path": "ml", "prediction": prediction, "quality": input_quality},
        )
        if user_id and input_quality == "sufficient":
            preview = _sanitize_preview(text, max_len=200)
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute(
                    f"INSERT INTO analyses (user_id, text_preview, prediction, confidence, real_prob, fake_prob, red_flag_score) VALUES ({ph(7)})",
                    (user_id, preview, prediction, confidence, real_prob, fake_prob, red_flag_score)
                )
                conn.commit()
                logger.info(f"Analysis saved for user {user_id}: {prediction} ({confidence_tier})")
            except Exception as e:
                logger.error(f"Failed to save analysis: {e}")
                conn.rollback()
            finally:
                conn.close()
        elif user_id and input_quality != "sufficient":
            logger.info(f"Analysis NOT saved — input too short ({input_quality}), skipping DB write")
        else:
            logger.info("No authenticated user — analysis not saved")

        # ── Word explainability (3.7) ──
        fake_words, real_words = _get_top_words(text)

        return PredictionResponse(
            prediction=prediction, confidence=confidence,
            confidence_tier=confidence_tier, input_quality=input_quality,
            real_probability=real_prob, fake_probability=fake_prob,
            red_flag_score=red_flag_score,
            fake_indicator_words=fake_words,
            real_indicator_words=real_words,
            model_version=MODEL_VERSION,
            timestamp=datetime.now().isoformat()
        )

    # ── AI Verification Endpoint (Groq — free, no billing required) ──

    # Legacy prompt (used when GNews is unavailable)
    AI_VERIFY_PROMPT_SIMPLE = """You are an expert media analyst. Evaluate this article for credibility.

ARTICLE:
{text}

EVALUATE:
1. Writing style — professional journalism or sensationalized?
2. Source attribution — named sources, or anonymous/vague?
3. Specificity — dates, names, verifiable details?
4. Tone — neutral and factual, or emotionally manipulative?
5. Red flags — conspiracy language, clickbait, ALL CAPS, fabricated quotes?

RESPOND IN THIS EXACT FORMAT (no markdown, no extra text):
CREDIBILITY: HIGH/MEDIUM/LOW
CONFIDENCE: 0-100
VERDICT: LIKELY_TRUE/MIXED/LIKELY_FALSE/UNVERIFIABLE
ANALYSIS: (2-3 sentence summary of key findings)"""

    # RAG-enhanced prompt (used when live news context is available)
    AI_VERIFY_PROMPT_RAG = """You are an expert fact-checker and media analyst with access to LIVE NEWS from trusted sources.

ARTICLE TO VERIFY:
{text}

LIVE NEWS CONTEXT (from real news sources, last 24 hours):
{live_context}

INSTRUCTIONS:
1. Compare the article's specific claims, names, dates, and statistics against the live news context above.
2. If multiple trusted sources corroborate the article's claims, this strongly suggests it is real.
3. If the live news contradicts the article's claims, or if no relevant coverage exists for extraordinary claims, this is suspicious.
4. Also evaluate writing style: professional journalism vs sensationalized/emotional/clickbait language.
5. Look for red flags: conspiracy language, ALL CAPS, "SHARE BEFORE DELETED", anonymous sources, miracle cures, etc.

RESPOND IN THIS EXACT FORMAT (no markdown, no extra text):
CREDIBILITY: HIGH/MEDIUM/LOW
CONFIDENCE: 0-100
VERDICT: LIKELY_TRUE/MIXED/LIKELY_FALSE/UNVERIFIABLE
ANALYSIS: (2-3 sentence summary comparing the article against live news evidence and writing quality)"""

    class GeminiRequest(BaseModel):
        text: str

    async def _run_gnews_search(text: str, *, lang: str | None = None):
        """Internal helper: run GNews search and return structured results."""
        gnews_key = os.getenv("GNEWS_API_KEY", "")
        if not gnews_key or len(text.strip()) < 10:
            return None

        try:
            from utils import extract_keywords
            keywords = extract_keywords(text, max_keywords=5)
            if not keywords:
                keywords = " ".join(text.split()[:5])

            from backend.http_client import get_client
            params = {
                "q": keywords,
                "apikey": gnews_key,
                "lang": lang or "en",
                "max": 10,
                "sortby": "relevance"
            }
            resp = await get_client().get("https://gnews.io/api/v4/search", params=params)
            if resp.status_code != 200:
                return None

            data = resp.json()
            articles = data.get("articles", []) if isinstance(data, dict) else []

            quality = []
            for a in articles:
                if a.get("title") and a.get("source", {}).get("name") and a.get("url"):
                    quality.append({
                        "title": a["title"],
                        "source": a["source"]["name"],
                        "url": a["url"],
                        "publishedAt": a.get("publishedAt", ""),
                        "description": a.get("description", ""),
                    })

            # Calculate web corroboration score
            trusted = ['reuters', 'apnews', 'bbc', 'nytimes', 'washingtonpost',
                       'theguardian', 'bloomberg', 'wsj', 'cnn', 'npr', 'pbs',
                       'abcnews', 'cbsnews', 'nbcnews', 'usatoday', 'associated press']
            trusted_count = sum(1 for a in quality if any(t in a["source"].lower() for t in trusted))
            total = len(quality)

            if total == 0:
                web_score = 0.3
            elif trusted_count >= 3:
                web_score = 0.9
            elif trusted_count >= 1:
                web_score = 0.7
            elif total >= 3:
                web_score = 0.5
            else:
                web_score = 0.4

            return {
                "web_score": web_score,
                "total_articles": total,
                "trusted_count": trusted_count,
                "articles": quality[:5],
                "keywords": keywords,
            }
        except Exception as e:
            logger.error(f"GNews search failed (internal): {e}")
            return None

    async def _call_groq(prompt_text: str):
        """Internal helper: call Groq LLaMA API and return parsed result."""
        groq_key = os.getenv("GROQ_API_KEY", "")
        if not groq_key:
            return None

        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "openai/gpt-oss-120b",
            "messages": [
                {"role": "system", "content": "You are an expert media analyst and fact-checker with access to live news feeds."},
                {"role": "user", "content": prompt_text}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        from backend.http_client import get_client
        resp = await get_client().post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=payload
        )

        if resp.status_code != 200:
            error_msg = resp.json().get("error", {}).get("message", resp.text[:200]) if resp.headers.get('content-type', '').startswith('application/json') else resp.text[:200]
            logger.error(f"Groq API error {resp.status_code}: {error_msg}")
            return None

        result_text = resp.json()["choices"][0]["message"]["content"] if resp.headers.get('content-type', '').startswith('application/json') else resp.text

        # Parse structured response
        credibility = "MEDIUM"
        confidence = 50
        verdict = "UNVERIFIABLE"
        analysis = result_text

        for line in result_text.upper().split("\n"):
            stripped = line.strip().lstrip("-* ")
            if stripped.startswith("CREDIBILITY"):
                for level in ["HIGH", "LOW", "MEDIUM"]:
                    if level in stripped:
                        credibility = level
                        break
            elif stripped.startswith("CONFIDENCE"):
                nums = re.findall(r'\d+', stripped)
                if nums:
                    confidence = min(100, max(0, int(nums[0])))
            elif stripped.startswith("VERDICT"):
                for v in ["LIKELY_TRUE", "LIKELY_FALSE", "MIXED", "UNVERIFIABLE"]:
                    if v in stripped:
                        verdict = v
                        break
            elif stripped.startswith("ANALYSIS"):
                for orig_line in result_text.split("\n"):
                    if orig_line.strip().upper().startswith("ANALYSIS"):
                        analysis = orig_line.split(":", 1)[-1].strip()
                        break

        score_map = {"HIGH": 0.85, "MEDIUM": 0.5, "LOW": 0.2}
        credibility_score = score_map.get(credibility, 0.5)

        return {
            "credibility": credibility,
            "credibility_score": credibility_score,
            "confidence": confidence,
            "verdict": verdict,
            "analysis": analysis,
        }

    # ── NEW: RAG-powered Smart Verify (GNews → Groq) ──

    @app.post("/api/v1/smart-verify")
    @limiter.limit("15/minute")
    async def smart_verify(req: GeminiRequest, request: Request):
        """
        RAG-powered verification: runs GNews FIRST, then injects live news
        context into the Groq LLaMA prompt for real-time fact-checking.
        """
        return await _run_smart_verify(req.text, source="web", user_id=_get_user_from_token(request))

    async def _run_smart_verify(text: str, *, source: str = "web", user_id: int | None = None) -> dict:
        """
        Core RAG verification logic, shared by the /smart-verify HTTP endpoint
        and the Telegram bot (backend/telegram_bot.py). Returns the same
        response dict the endpoint returns.

        ``source``/``user_id`` are used only for §5 metrics logging.
        """
        text = text.strip()[:3000]
        if len(text) < 10:
            raise HTTPException(400, "Text too short for verification")

        # Check cache first (Tier 1 Upgrade 3)
        cached = claim_cache.get(text, "smart-verify")
        claim_hash = claim_cache._normalize_key(text, "smart-verify")
        if cached:
            cached["cache_status"] = "hit"
            cached["claim_hash"] = claim_hash
            logger.info("Cache HIT for smart-verify")
            # Cache hit = a real check, but zero marginal LLM cost.
            _metrics.log_event(
                _metrics.EVENT_CHECK, user_id=user_id, source=source, cost_usd=0.0,
                meta={"path": "rag", "cache": "hit"},
            )
            return cached

        # Phase 10.1: Detect Indic/Hindi text for smart routing
        try:
            from backend.lang_detect import detect_language
            lang_info = detect_language(text)
        except Exception:
            lang_info = {"script": "latin", "lang": "en", "indic_ratio": 0.0, "is_indic": False}

        # Step 1: Run GNews search for live context (use detected language)
        gnews_lang = lang_info["lang"] if lang_info["is_indic"] and lang_info["lang"] not in ("hinglish",) else "en"
        gnews_result = await _run_gnews_search(text, lang=gnews_lang)
        # Also try English GNews if Indic search returned nothing
        if lang_info["is_indic"] and (not gnews_result or gnews_result.get("total_articles", 0) == 0):
            gnews_result = await _run_gnews_search(text, lang="en")

        # Step 2: Build the prompt — RAG or simple depending on GNews results
        if gnews_result and gnews_result["total_articles"] > 0:
            # Build live context block from search results
            context_lines = []
            for i, a in enumerate(gnews_result["articles"][:5], 1):
                pub = a.get("publishedAt", "")[:10] or "recent"
                desc = a.get("description", "")[:120]
                context_lines.append(f"{i}. [{a['source']}] \"{a['title']}\" — {pub}\n   {desc}")
            live_context = "\n".join(context_lines) if context_lines else "No relevant live news found."

            prompt = AI_VERIFY_PROMPT_RAG.format(text=text, live_context=live_context)
            # Inject Indic instruction if needed
            if lang_info["is_indic"]:
                indic_prefix = (f"IMPORTANT: The article below is written in {lang_info['lang'].upper()} "
                                f"({lang_info['script']} script). Read and understand it in its original language, "
                                f"but ALWAYS respond in English using the exact format below.\n\n")
                prompt = indic_prefix + prompt
            logger.info(f"Smart verify: RAG mode with {gnews_result['total_articles']} articles (lang={lang_info['lang']})")
        else:
            # Fallback: no live context available
            prompt = AI_VERIFY_PROMPT_SIMPLE.format(text=text)
            if lang_info["is_indic"]:
                indic_prefix = (f"IMPORTANT: The article below is written in {lang_info['lang'].upper()} "
                                f"({lang_info['script']} script). Read and understand it in its original language, "
                                f"but ALWAYS respond in English using the exact format below.\n\n")
                prompt = indic_prefix + prompt
            logger.info(f"Smart verify: fallback mode (lang={lang_info['lang']})")

        # Step 3: Call Groq with the enriched prompt
        ai_result = await _call_groq(prompt)

        if not ai_result:
            groq_key = os.getenv("GROQ_API_KEY", "")
            if not groq_key:
                raise HTTPException(503, "AI verification not configured. Set GROQ_API_KEY env var.")
            raise HTTPException(502, "AI verification failed")

        # Step 4: Return combined response
        response = {
            **ai_result,
            "available": True,
            "mode": "rag" if (gnews_result and gnews_result["total_articles"] > 0) else "standalone",
            "detected_lang": lang_info["lang"],
            "is_indic": lang_info["is_indic"],
        }

        # Attach web search results so frontend can update both rings
        if gnews_result:
            response["web"] = {
                "web_score": gnews_result["web_score"],
                "total_articles": gnews_result["total_articles"],
                "trusted_count": gnews_result["trusted_count"],
                "articles": gnews_result["articles"],
                "keywords": gnews_result["keywords"],
                "available": True,
            }
        else:
            response["web"] = {
                "web_score": 0.3,
                "total_articles": 0,
                "trusted_count": 0,
                "articles": [],
                "keywords": "",
                "available": False,
            }

        response["cache_status"] = "miss"
        response["claim_hash"] = claim_hash
        claim_cache.set(text, "smart-verify", response)
        
        # Save to DB for SEO pages (Phase 11.2)
        try:
            from backend.claims_db import save_seo_claim
            save_seo_claim(claim_hash, text, response)
        except Exception as e:
            logger.error(f"Failed to save seo claim: {e}")

        # Cache miss = one Groq call (+ a GNews call when live context was found).
        gnews_hit = bool(gnews_result and gnews_result.get("total_articles", 0) > 0)
        _metrics.log_event(
            _metrics.EVENT_CHECK, user_id=user_id, source=source,
            cost_usd=_metrics.estimate_rag_cost(groq_calls=1, gnews_calls=1 if gnews_hit else 0),
            meta={"path": "rag", "cache": "miss", "mode": response["mode"]},
        )
        return response

    # ── Google Fact Check API Integration ──
    GOOGLE_FACTCHECK_API_KEY = os.getenv("GOOGLE_FACTCHECK_API_KEY", "")

    async def _run_factcheck_search(text: str):
        """Search Google Fact Check API for existing fact-checks matching this claim.
        Uses Google's ClaimReview database which indexes 200+ fact-checking orgs
        including AFP, Snopes, PolitiFact, AltNews, BoomLive, PIB India.
        """
        if not GOOGLE_FACTCHECK_API_KEY or len(text.strip()) < 10:
            return None

        try:
            from utils import extract_keywords
            keywords = extract_keywords(text, max_keywords=5)
            if not keywords:
                keywords = " ".join(text.split()[:8])

            from backend.http_client import get_client
            params = {
                "query": keywords,
                "key": GOOGLE_FACTCHECK_API_KEY,
                "languageCode": "en",
            }
            resp = await get_client().get(
                "https://factchecktools.googleapis.com/v1alpha1/claims:search",
                params=params
            )
            if resp.status_code != 200:
                logger.warning(f"Fact Check API returned status {resp.status_code}")
                return None

            data = resp.json()
            claims = data.get("claims", [])

            if not claims:
                return {
                    "found": False,
                    "total_claims": 0,
                    "reviews": [],
                    "factcheck_score": 0.5,  # Neutral — no data
                }

            reviews = []
            verdict_scores = []
            for claim in claims[:5]:
                claim_text = claim.get("text", "")
                claimant = claim.get("claimant", "Unknown")
                for review in claim.get("claimReview", []):
                    publisher = review.get("publisher", {}).get("name", "Unknown")
                    url = review.get("url", "")
                    title = review.get("title", "")
                    rating = review.get("textualRating", "").lower()
                    review_date = review.get("reviewDate", "")[:10]

                    # Convert textual ratings to numeric score (0 = definitely false, 1 = definitely true)
                    false_indicators = ["false", "fake", "pants on fire", "misleading",
                                        "mostly false", "incorrect", "wrong", "hoax",
                                        "fabricated", "scam", "satire", "no evidence",
                                        "unproven", "not true", "manipulated"]
                    true_indicators = ["true", "correct", "accurate", "mostly true",
                                       "verified", "confirmed", "real", "factual"]
                    mixed_indicators = ["half true", "mixture", "partly", "partially",
                                        "needs context", "missing context", "exaggerated"]

                    if any(ind in rating for ind in false_indicators):
                        score = 0.15
                    elif any(ind in rating for ind in true_indicators):
                        score = 0.9
                    elif any(ind in rating for ind in mixed_indicators):
                        score = 0.5
                    else:
                        score = 0.5  # Unknown rating

                    verdict_scores.append(score)
                    reviews.append({
                        "claim": claim_text[:200],
                        "claimant": claimant,
                        "publisher": publisher,
                        "rating": review.get("textualRating", "Unknown"),
                        "url": url,
                        "title": title[:150],
                        "date": review_date,
                        "score": score,
                    })

            # Overall fact-check score: average of all verdict scores
            avg_score = sum(verdict_scores) / len(verdict_scores) if verdict_scores else 0.5

            return {
                "found": True,
                "total_claims": len(claims),
                "reviews": reviews[:5],
                "factcheck_score": round(avg_score, 2),
            }

        except Exception as e:
            logger.error(f"Fact Check API search failed: {e}")
            return None

    @app.post("/api/v1/fact-check")
    @limiter.limit("15/minute")
    async def fact_check_search(req: GeminiRequest, request: Request):
        """Search Google's Fact Check database for existing fact-checks on a claim."""
        text = req.text.strip()[:3000]
        if len(text) < 10:
            raise HTTPException(400, "Text too short for fact-check search")

        # Check cache first
        cached = claim_cache.get(text, "fact-check")
        if cached:
            cached["cache_status"] = "hit"
            return cached

        result = await _run_factcheck_search(text)

        if result is None:
            if not GOOGLE_FACTCHECK_API_KEY:
                return {
                    "available": False,
                    "found": False,
                    "total_claims": 0,
                    "reviews": [],
                    "factcheck_score": 0.5,
                    "message": "Fact Check API not configured. Set GOOGLE_FACTCHECK_API_KEY env var."
                }
            return {
                "available": False,
                "found": False,
                "total_claims": 0,
                "reviews": [],
                "factcheck_score": 0.5,
                "message": "Fact Check search failed"
            }

        result_response = {**result, "available": True, "cache_status": "miss"}
        claim_cache.set(text, "fact-check", result_response)
        return result_response

    # ── Google Safe Browsing API Integration ──
    GOOGLE_SAFE_BROWSING_API_KEY = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")

    def _extract_urls_from_text(text: str):
        """Extract all URLs from article text."""
        url_pattern = r'https?://(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?'
        urls = re.findall(url_pattern, text)
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for u in urls:
            u_clean = u.rstrip('.,;:!?)\'\"')
            if u_clean not in seen:
                seen.add(u_clean)
                unique.append(u_clean)
        return unique[:20]  # Cap at 20 URLs

    async def _check_safe_browsing(urls: list):
        """Check URLs against Google Safe Browsing API.
        Returns threat info for any flagged URLs.
        """
        if not GOOGLE_SAFE_BROWSING_API_KEY or not urls:
            return None

        try:
            from backend.http_client import get_client
            payload = {
                "client": {
                    "clientId": "fake-news-detector",
                    "clientVersion": APP_VERSION
                },
                "threatInfo": {
                    "threatTypes": [
                        "MALWARE",
                        "SOCIAL_ENGINEERING",
                        "UNWANTED_SOFTWARE",
                        "POTENTIALLY_HARMFUL_APPLICATION"
                    ],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": u} for u in urls]
                }
            }

            resp = await get_client().post(
                f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GOOGLE_SAFE_BROWSING_API_KEY}",
                json=payload
            )

            if resp.status_code != 200:
                logger.warning(f"Safe Browsing API returned status {resp.status_code}")
                return None

            data = resp.json()
            matches = data.get("matches", [])

            threats = []
            threat_types_found = set()
            for match in matches:
                url = match.get("threat", {}).get("url", "")
                threat_type = match.get("threatType", "UNKNOWN")
                platform = match.get("platformType", "UNKNOWN")
                threat_types_found.add(threat_type)

                # Human-readable threat descriptions
                threat_labels = {
                    "MALWARE": "Malware Distribution",
                    "SOCIAL_ENGINEERING": "Phishing / Social Engineering",
                    "UNWANTED_SOFTWARE": "Unwanted Software",
                    "POTENTIALLY_HARMFUL_APPLICATION": "Harmful Application"
                }

                threats.append({
                    "url": url,
                    "threat_type": threat_type,
                    "threat_label": threat_labels.get(threat_type, threat_type),
                    "platform": platform,
                })

            # Safety score: 1.0 = all safe, 0.0 = all dangerous
            if not urls:
                safety_score = 1.0
            else:
                flagged_count = len(set(t["url"] for t in threats))
                safety_score = 1.0 - (flagged_count / len(urls))

            return {
                "urls_checked": len(urls),
                "urls_flagged": len(threats),
                "threats": threats,
                "threat_types": list(threat_types_found),
                "safety_score": round(safety_score, 2),
                "all_safe": len(threats) == 0,
            }

        except Exception as e:
            logger.error(f"Safe Browsing API check failed: {e}")
            return None

    @app.post("/api/v1/safe-browsing")
    @limiter.limit("15/minute")
    async def safe_browsing_check(req: GeminiRequest, request: Request):
        """Check URLs in article text against Google Safe Browsing database."""
        text = req.text.strip()[:5000]
        if len(text) < 10:
            raise HTTPException(400, "Text too short")

        # Extract URLs from the article text
        urls = _extract_urls_from_text(text)

        # Check cache first (only if URLs exist — no point caching empty results)
        if urls:
            cached = claim_cache.get(text, "safe-browsing")
            if cached:
                cached["cache_status"] = "hit"
                return cached

        if not urls:
            return {
                "available": True,
                "urls_checked": 0,
                "urls_flagged": 0,
                "threats": [],
                "threat_types": [],
                "safety_score": 1.0,
                "all_safe": True,
                "message": "No URLs found in text"
            }

        if not GOOGLE_SAFE_BROWSING_API_KEY:
            return {
                "available": False,
                "urls_checked": len(urls),
                "urls_flagged": 0,
                "threats": [],
                "threat_types": [],
                "safety_score": 1.0,
                "all_safe": True,
                "message": "Safe Browsing API not configured. Set GOOGLE_SAFE_BROWSING_API_KEY env var."
            }

        result = await _check_safe_browsing(urls)

        if result is None:
            return {
                "available": False,
                "urls_checked": len(urls),
                "urls_flagged": 0,
                "threats": [],
                "threat_types": [],
                "safety_score": 1.0,
                "all_safe": True,
                "message": "Safe Browsing check failed"
            }

        sb_response = {**result, "available": True, "urls_found": urls, "cache_status": "miss"}
        claim_cache.set(text, "safe-browsing", sb_response)
        return sb_response

    @app.get("/api/v1/cache-stats")
    async def cache_stats():
        """Return claim cache hit/miss statistics for monitoring."""
        return claim_cache.stats()

    @app.get("/api/v1/claim/{claim_hash}", tags=["SEO"])
    def get_seo_claim_endpoint(claim_hash: str):
        """Fetch a verified claim by its unique hash for public SEO pages."""
        try:
            from backend.claims_db import get_seo_claim
            claim = get_seo_claim(claim_hash)
            if not claim:
                raise HTTPException(404, "Claim not found")
            return claim
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching claim: {e}")
            raise HTTPException(500, "Internal server error")

    # ── Phase 9.2: Shareable Verdict Card (SVG) ──

    @app.get("/api/v1/claim/{claim_hash}/card.svg", tags=["SEO"])
    def get_claim_card_svg(claim_hash: str):
        """Generate a shareable SVG verdict card for social media previews."""
        from backend.claims_db import get_seo_claim
        from backend.card_generator import generate_verdict_card
        from fastapi.responses import Response

        claim = get_seo_claim(claim_hash)
        if not claim:
            raise HTTPException(404, "Claim not found")

        svg = generate_verdict_card(
            claim_text=claim.get("claim_text", claim.get("text", "Claim text unavailable")),
            verdict=claim.get("verdict", "UNVERIFIABLE"),
            confidence=claim.get("confidence", 0),
            analysis=claim.get("analysis", ""),
        )
        return Response(content=svg, media_type="image/svg+xml",
                        headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/claim/{claim_hash}", tags=["SEO"])
    def claim_og_page(claim_hash: str, request: Request):
        """Server-rendered HTML with OG meta tags for social crawlers.
        Regular browsers get redirected to the SPA; crawlers get meta tags."""
        from backend.claims_db import get_seo_claim
        from fastapi.responses import HTMLResponse

        ua = (request.headers.get("user-agent") or "").lower()
        is_crawler = any(bot in ua for bot in [
            "whatsapp", "telegrambot", "twitterbot", "facebookexternalhit",
            "linkedinbot", "slackbot", "googlebot", "bingbot", "discordbot",
        ])

        claim = get_seo_claim(claim_hash)
        if not claim and not is_crawler:
            # Regular browser — let the SPA handle the 404
            return HTMLResponse(status_code=200, content=_build_spa_redirect(claim_hash))

        if not claim:
            raise HTTPException(404, "Claim not found")

        # Extract data for meta tags
        import html as html_mod
        verdict = claim.get("verdict", "UNVERIFIABLE").replace("_", " ")
        confidence = claim.get("confidence", 0)
        text = claim.get("claim_text", claim.get("text", ""))[:200]
        analysis = claim.get("analysis", "")[:300]
        safe_text = html_mod.escape(text)
        safe_analysis = html_mod.escape(analysis)
        base_url = "https://fake-news-detector-8djq.onrender.com"
        card_url = f"{base_url}/api/v1/claim/{claim_hash}/card.svg"
        page_url = f"{base_url}/claim/{claim_hash}"

        title = f"VerifAI: {verdict} ({confidence:.0f}% confidence)"
        description = safe_analysis if safe_analysis else f'Claim: "{safe_text[:120]}..."'

        if is_crawler:
            # Build JSON-LD structured data for Google Fact Check
            import json as json_mod
            verdict_name_map = {"LIKELY_TRUE": "True", "LIKELY_FALSE": "False", "MIXED": "Mixture", "UNVERIFIABLE": "Unverifiable"}
            rating_val_map = {"LIKELY_TRUE": 4, "LIKELY_FALSE": 1, "MIXED": 3, "UNVERIFIABLE": 3}
            jsonld = json_mod.dumps({
                "@context": "https://schema.org",
                "@type": "ClaimReview",
                "url": page_url,
                "claimReviewed": text[:500],
                "author": {"@type": "Organization", "name": "VerifAI", "url": base_url},
                "reviewRating": {
                    "@type": "Rating",
                    "ratingValue": rating_val_map.get(claim.get("verdict", ""), 3),
                    "bestRating": 5, "worstRating": 1,
                    "alternateName": verdict_name_map.get(claim.get("verdict", ""), "Unverifiable"),
                },
                "itemReviewed": {"@type": "Claim", "name": text[:200]},
            })

            # Crawlers get a lightweight HTML with OG tags + JSON-LD
            og_html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<title>{title}</title>
<meta name="description" content="{description}"/>
<link rel="canonical" href="{page_url}"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{description}"/>
<meta property="og:image" content="{card_url}"/>
<meta property="og:image:width" content="1200"/>
<meta property="og:image:height" content="630"/>
<meta property="og:url" content="{page_url}"/>
<meta property="og:type" content="article"/>
<meta property="og:site_name" content="VerifAI Fact Checker"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{title}"/>
<meta name="twitter:description" content="{description}"/>
<meta name="twitter:image" content="{card_url}"/>
<script type="application/ld+json">{jsonld}</script>
</head><body><h1>{title}</h1><p>{description}</p>
<p><a href="{page_url}">View full report on VerifAI</a></p>
</body></html>"""
            return HTMLResponse(content=og_html)

        # Regular browser — serve SPA shell with injected OG tags
        return HTMLResponse(content=_build_spa_redirect(claim_hash, title=title,
                            description=description, card_url=card_url, page_url=page_url))

    def _build_spa_redirect(claim_hash: str, *, title: str = "VerifAI Fact Checker",
                            description: str = "AI-powered fact checking",
                            card_url: str = "", page_url: str = "") -> str:
        """Build a minimal HTML page that loads the React SPA for a claim page."""
        base_url = "https://fake-news-detector-8djq.onrender.com"
        if not page_url:
            page_url = f"{base_url}/claim/{claim_hash}"
        if not card_url:
            card_url = f"{base_url}/api/v1/claim/{claim_hash}/card.svg"

        return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title}</title>
<meta name="description" content="{description}"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{description}"/>
<meta property="og:image" content="{card_url}"/>
<meta property="og:image:width" content="1200"/>
<meta property="og:image:height" content="630"/>
<meta property="og:url" content="{page_url}"/>
<meta property="og:type" content="article"/>
<meta property="og:site_name" content="VerifAI Fact Checker"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{title}"/>
<meta name="twitter:description" content="{description}"/>
<meta name="twitter:image" content="{card_url}"/>
<script>window.location.replace('/claim/{claim_hash}');</script>
</head><body>
<noscript><a href="/claim/{claim_hash}">View report</a></noscript>
</body></html>"""

    # ── Phase 11.2: SEO Infrastructure (Sitemap, Robots, JSON-LD) ──

    @app.get("/sitemap.xml", tags=["SEO"])
    def sitemap_xml():
        """Dynamic XML sitemap listing all verified claim pages."""
        from backend.claims_db import list_all_claim_hashes
        from fastapi.responses import Response

        base = "https://fake-news-detector-8djq.onrender.com"
        claims = list_all_claim_hashes()

        urls = [f"""  <url>
    <loc>{base}/claim/{c['hash']}</loc>
    <lastmod>{c['created_at'][:10] if c.get('created_at') else '2026-01-01'}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>""" for c in claims]

        # Add static pages
        static_pages = [
            ("", "daily", "1.0"),
            ("/about", "monthly", "0.5"),
        ]
        for path, freq, prio in static_pages:
            urls.insert(0, f"""  <url>
    <loc>{base}{path}</loc>
    <changefreq>{freq}</changefreq>
    <priority>{prio}</priority>
  </url>""")

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
        return Response(content=xml, media_type="application/xml",
                        headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/robots.txt", tags=["SEO"])
    def robots_txt():
        """Serve robots.txt pointing crawlers to the sitemap."""
        from fastapi.responses import PlainTextResponse
        base = "https://fake-news-detector-8djq.onrender.com"
        return PlainTextResponse(
            f"User-agent: *\nAllow: /\nAllow: /claim/\nDisallow: /api/\nDisallow: /dashboard\nDisallow: /settings\n\nSitemap: {base}/sitemap.xml\n",
            headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/api/v1/claim/{claim_hash}/jsonld", tags=["SEO"])
    def claim_jsonld(claim_hash: str):
        """Return ClaimReview JSON-LD structured data for Google's fact-check panel."""
        from backend.claims_db import get_seo_claim

        claim = get_seo_claim(claim_hash)
        if not claim:
            raise HTTPException(404, "Claim not found")

        import html as html_mod
        verdict = claim.get("verdict", "UNVERIFIABLE")
        confidence = claim.get("confidence", 0)
        text = claim.get("claim_text", claim.get("text", ""))
        analysis = claim.get("analysis", "")
        base_url = "https://fake-news-detector-8djq.onrender.com"

        # Map internal verdict to ClaimReview alternateName
        rating_map = {
            "LIKELY_TRUE": {"name": "True", "val": 4, "best": 5, "worst": 1},
            "LIKELY_FALSE": {"name": "False", "val": 1, "best": 5, "worst": 1},
            "MIXED": {"name": "Mixture", "val": 3, "best": 5, "worst": 1},
            "UNVERIFIABLE": {"name": "Unverifiable", "val": 3, "best": 5, "worst": 1},
        }
        rating = rating_map.get(verdict, rating_map["UNVERIFIABLE"])

        jsonld = {
            "@context": "https://schema.org",
            "@type": "ClaimReview",
            "url": f"{base_url}/claim/{claim_hash}",
            "claimReviewed": text[:500],
            "author": {
                "@type": "Organization",
                "name": "VerifAI",
                "url": base_url,
            },
            "reviewRating": {
                "@type": "Rating",
                "ratingValue": rating["val"],
                "bestRating": rating["best"],
                "worstRating": rating["worst"],
                "alternateName": rating["name"],
            },
            "itemReviewed": {
                "@type": "Claim",
                "name": text[:200],
                "appearance": {
                    "@type": "CreativeWork",
                    "url": f"{base_url}/claim/{claim_hash}",
                },
            },
        }
        return jsonld

    # ── Source Credibility Database — Tier 2 Upgrade 1 ──
    # Comprehensive domain reputation database with India-first focus.
    # Each entry: (credibility_score 0-100, category, bias, description)

    # Source Credibility DB (moved to backend/credibility_db.py)
    from backend.credibility_db import SOURCE_CREDIBILITY_DB

    def _check_source_credibility(text: str) -> dict:
        """Extract domains from text and check their credibility scores."""
        urls = _extract_urls_from_text(text)
        if not urls:
            return {"sources_found": 0, "sources": [], "avg_credibility": None}

        sources = []
        seen_domains = set()

        for url in urls:
            try:
                from urllib.parse import urlparse as _urlparse
                parsed = _urlparse(url)
                domain = parsed.netloc.replace("www.", "").lower()
            except Exception:
                continue

            if not domain or domain in seen_domains:
                continue
            seen_domains.add(domain)

            # Check exact match first, then partial match
            entry = SOURCE_CREDIBILITY_DB.get(domain)
            if not entry:
                # Try partial match (e.g., "m.ndtv.com" → "ndtv.com")
                for known_domain, data in SOURCE_CREDIBILITY_DB.items():
                    if domain.endswith(known_domain) or known_domain in domain:
                        entry = data
                        break

            if entry:
                score, category, bias, desc = entry
                tier = "gold" if score >= 93 else "trusted" if score >= 80 else "mixed" if score >= 50 else "unreliable"
                sources.append({
                    "domain": domain,
                    "url": url,
                    "credibility_score": score,
                    "category": category,
                    "bias": bias,
                    "description": desc,
                    "tier": tier,
                    "known": True,
                })
            else:
                sources.append({
                    "domain": domain,
                    "url": url,
                    "credibility_score": 50,
                    "category": "unknown",
                    "bias": "unknown",
                    "description": "Domain not in credibility database",
                    "tier": "unknown",
                    "known": False,
                })

        # Calculate average credibility
        known_sources = [s for s in sources if s["known"]]
        avg_cred = round(sum(s["credibility_score"] for s in known_sources) / len(known_sources), 1) if known_sources else None

        return {
            "sources_found": len(sources),
            "known_sources": len(known_sources),
            "unknown_sources": len(sources) - len(known_sources),
            "avg_credibility": avg_cred,
            "sources": sources,
            "database_size": len(SOURCE_CREDIBILITY_DB),
        }

    @app.post("/api/v1/source-credibility")
    @limiter.limit("20/minute")
    async def check_source_credibility(req: GeminiRequest, request: Request):
        """Check credibility of news sources/domains found in article text."""
        text = req.text.strip()[:5000]
        if len(text) < 10:
            raise HTTPException(400, "Text too short")

        # Check cache first
        cached = claim_cache.get(text, "source-credibility")
        if cached:
            cached["cache_status"] = "hit"
            return cached

        result = _check_source_credibility(text)
        result["available"] = True
        result["cache_status"] = "miss"
        claim_cache.set(text, "source-credibility", result)
        return result

    # India Threat Scanner (moved to backend/threat_patterns.py)
    from backend.threat_patterns import INDIA_THREAT_PATTERNS, scan_india_threats as _scan_india_threats

    @app.post("/api/v1/india-threat-scan")
    @limiter.limit("20/minute")
    async def india_threat_scan(req: GeminiRequest, request: Request):
        """Scan article text for India-specific misinformation and scam patterns."""
        text = req.text.strip()[:5000]
        if len(text) < 10:
            raise HTTPException(400, "Text too short")

        cached = claim_cache.get(text, "india-threat")
        if cached:
            cached["cache_status"] = "hit"
            return cached

        result = _scan_india_threats(text)
        result["available"] = True
        result["cache_status"] = "miss"
        claim_cache.set(text, "india-threat", result)
        return result

    # ── Telegram bot webhook (Phase 9.1) ──
    # Thin adapter over _run_smart_verify + _scan_india_threats. Puts VerifAI
    # inside the chat apps where misinformation actually spreads.
    import backend.telegram_bot as tg

    # Light global daily-call ceiling so a viral spike can't run up the Groq/GNews
    # bill (roadmap Rule 2). In-memory; resets when the UTC date changes.
    _tg_budget = {"date": "", "count": 0}
    _TG_DAILY_LIMIT = int(os.getenv("TELEGRAM_DAILY_LIMIT", "500"))

    def _tg_budget_ok() -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        if _tg_budget["date"] != today:
            _tg_budget["date"] = today
            _tg_budget["count"] = 0
        if _tg_budget["count"] >= _TG_DAILY_LIMIT:
            return False
        _tg_budget["count"] += 1
        return True

    async def _tg_handle_check(chat_id: int, text: str):
        """Background task: verify a claim and send the result back to the chat."""
        try:
            verify = await _run_smart_verify(text, source="telegram")
        except HTTPException as e:
            await tg.send_message(chat_id, f"⚠️ {tg._esc(e.detail)}")
            return
        except Exception as e:  # noqa: BLE001
            logger.error(f"Telegram check failed: {e}")
            await tg.send_message(chat_id, "⚠️ Something went wrong while checking. Please try again.")
            return

        threat = None
        try:
            threat = _scan_india_threats(text)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Telegram threat scan failed (non-fatal): {e}")

        await tg.send_message(chat_id, tg.format_verdict_reply(verify, threat))

    @app.post("/api/v1/telegram/webhook/{secret}")
    async def telegram_webhook(secret: str, request: Request):
        """Receive Telegram updates. Validates a shared secret, replies fast, and
        processes the verification in the background."""
        import asyncio

        expected = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        # Constant-time-ish comparison; reject silently (200 no-op) to avoid probing.
        if not expected or secret != expected or header_secret != expected:
            logger.warning("Telegram webhook: secret mismatch — ignoring")
            return {"ok": True}

        try:
            update = await request.json()
        except Exception:
            return {"ok": True}

        parsed = tg.parse_update(update)
        if not parsed:
            return {"ok": True}

        chat_id = parsed["chat_id"]
        command = parsed["command"]
        text = parsed["text"]

        if command in ("/start",):
            await tg.send_message(chat_id, tg.WELCOME_TEXT)
            return {"ok": True}
        if command in ("/help",):
            await tg.send_message(chat_id, tg.HELP_TEXT)
            return {"ok": True}
        if command:
            await tg.send_message(chat_id, tg.HELP_TEXT)
            return {"ok": True}

        if not text or len(text.strip()) < 10:
            await tg.send_message(
                chat_id,
                "Send me a claim, headline, or forwarded message (at least a sentence) and I'll check it. /help for tips.",
            )
            return {"ok": True}

        if not tg.allow_request(chat_id):
            await tg.send_message(chat_id, "⏳ You're checking too fast — please wait a moment and try again.")
            return {"ok": True}

        if not _tg_budget_ok():
            await tg.send_message(chat_id, "🛌 VerifAI has hit its free daily check limit. Please try again tomorrow.")
            return {"ok": True}

        await tg.send_message(chat_id, tg.CHECKING_TEXT)
        asyncio.create_task(_tg_handle_check(chat_id, text))
        return {"ok": True}

    # ── Voice Transcription — Upgrade 6 ──
    # Uses Groq Whisper API to transcribe audio files (WhatsApp voice notes, recordings)
    # then feeds the transcript into the full analysis pipeline.

    @app.post("/api/v1/transcribe")
    @limiter.limit("10/minute")
    async def transcribe_audio(request: Request, audio: UploadFile = File(...)):
        """Transcribe an audio file using Groq Whisper, return the text."""
        groq_key = os.getenv("GROQ_API_KEY", "")
        if not groq_key:
            raise HTTPException(503, "Transcription not configured. Set GROQ_API_KEY env var.")

        # Validate file type
        allowed_types = {
            "audio/wav", "audio/wave", "audio/x-wav",
            "audio/mpeg", "audio/mp3",
            "audio/ogg", "audio/opus",
            "audio/mp4", "audio/m4a", "audio/x-m4a",
            "audio/webm",
            "audio/flac",
        }
        content_type = (audio.content_type or "").lower()
        filename = (audio.filename or "audio.wav").lower()
        allowed_exts = {".wav", ".mp3", ".ogg", ".opus", ".m4a", ".mp4", ".webm", ".flac"}
        ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""

        if content_type not in allowed_types and ext not in allowed_exts:
            raise HTTPException(400, f"Unsupported audio format: {content_type}. Use WAV, MP3, OGG, M4A, or WebM.")

        # Read file (max 25MB — Groq limit)
        audio_bytes = await audio.read()
        if len(audio_bytes) > 25 * 1024 * 1024:
            raise HTTPException(400, "Audio file too large. Maximum size is 25MB.")
        if len(audio_bytes) < 1000:
            raise HTTPException(400, "Audio file too small — likely empty or corrupted.")

        try:
            from backend.http_client import get_client

            # Send to Groq Whisper API (multipart form requires httpx Files)
            resp = await get_client().post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {groq_key}"},
                files={"file": (audio.filename or "audio.wav", audio_bytes, content_type or "audio/wav")},
                data={
                    "model": "whisper-large-v3",
                    "response_format": "verbose_json",
                    "language": "",
                },
                timeout=30.0
            )

            if resp.status_code != 200:
                logger.error(f"Groq Whisper API error: {resp.status_code} — {resp.text[:200]}")
                raise HTTPException(502, f"Transcription service error: {resp.status_code}")

            result = resp.json()
            transcript = result.get("text", "").strip()

            if not transcript:
                return {
                    "success": False,
                    "transcript": "",
                    "message": "No speech detected in the audio file.",
                    "language": result.get("language", "unknown"),
                }

            return {
                "success": True,
                "transcript": transcript,
                "language": result.get("language", "unknown"),
                "duration": result.get("duration", 0),
                "word_count": len(transcript.split()),
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise HTTPException(500, "Transcription failed. Please try a different audio file.")

    # ── Community Dashboard — Upgrade 8 ──
    # Public anonymized stats showing platform-wide analysis trends.

    @app.get("/api/v1/community-stats")
    async def community_stats():
        """Return anonymized, aggregated community statistics."""
        try:
            # Total analyses
            total_row = execute_db("SELECT COUNT(*) FROM analyses", fetch="one")
            total = total_row[0] if total_row else 0

            # Real vs Fake breakdown
            breakdown_rows = execute_db("SELECT prediction, COUNT(*) FROM analyses GROUP BY prediction", fetch="all")
            breakdown = dict(breakdown_rows) if breakdown_rows else {}
            fake_count = breakdown.get("FAKE", 0)
            real_count = breakdown.get("REAL", 0)

            # Average confidence
            avg_row = execute_db("SELECT COALESCE(AVG(confidence), 0) FROM analyses", fetch="one")
            avg_confidence = round(avg_row[0], 1) if avg_row else 0.0

            # High-confidence fakes (confidence >= 80)
            high_conf_row = execute_db("SELECT COUNT(*) FROM analyses WHERE prediction = 'FAKE' AND confidence >= 80", fetch="one")
            high_conf_fake = high_conf_row[0] if high_conf_row else 0

            # Recent 7-day trend (M4 FIX: cross-DB compatible date expression)
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            date_expr = "created_at::DATE" if USE_POSTGRES else "DATE(created_at)"

            trend_rows = execute_db(f"""
                SELECT {date_expr} as day, prediction, COUNT(*)
                FROM analyses
                WHERE created_at >= {ph()}
                GROUP BY day, prediction
                ORDER BY day
            """, (seven_days_ago,), fetch="all")

            daily_trend = {}
            if trend_rows:
                for day, pred, cnt in trend_rows:
                    day_str = str(day)[:10]
                    if day_str not in daily_trend:
                        daily_trend[day_str] = {"date": day_str, "real": 0, "fake": 0, "total": 0}
                    daily_trend[day_str][pred.lower()] = cnt
                    daily_trend[day_str]["total"] += cnt
            trend_data = list(daily_trend.values())

            # Average red flag score (M4 FIX: use execute_db instead of undefined cursor)
            red_flag_row = execute_db("SELECT COALESCE(AVG(red_flag_score), 0) FROM analyses WHERE red_flag_score > 0", fetch="one")
            avg_red_flag = round(red_flag_row[0] * 100, 1) if red_flag_row else 0.0

            # Today's count (M4 FIX: cross-DB compatible 'today' expression)
            today_expr = "CURRENT_DATE" if USE_POSTGRES else "DATE('now')"
            today_row = execute_db(f"SELECT COUNT(*) FROM analyses WHERE {date_expr} = {today_expr}", fetch="one")
            today_count = today_row[0] if today_row else 0

        except Exception as e:
            logger.error(f"Community stats query failed: {e}")
            return {
                "available": False,
                "message": "Stats temporarily unavailable",
                "total_analyses": 0,
            }

        # Cache stats
        cache_data = claim_cache.stats()

        # Fake percentage
        fake_pct = round(fake_count / total * 100, 1) if total > 0 else 0

        return {
            "available": True,
            "total_analyses": total,
            "today_analyses": today_count,
            "breakdown": {
                "fake": fake_count,
                "real": real_count,
                "fake_percentage": fake_pct,
                "real_percentage": round(100 - fake_pct, 1),
            },
            "avg_confidence": avg_confidence,
            "avg_red_flag_score": avg_red_flag,
            "high_confidence_fakes": high_conf_fake,
            "trend_7d": trend_data,
            "cache": {
                "size": cache_data["cache_size"],
                "hits": cache_data["hits"],
                "misses": cache_data["misses"],
                "hit_rate": cache_data["hit_rate"],
            },
            "platform": {
                "version": APP_VERSION,
                "endpoints": len({r.path for r in app.routes if getattr(r, "path", "").startswith("/api/v1/")}),
                "source_db_size": len(SOURCE_CREDIBILITY_DB),
                "threat_categories": len(INDIA_THREAT_PATTERNS),
            },
        }

    # ── LEGACY: Keep old endpoints as fallbacks ──

    @app.post("/api/v1/gemini-verify")
    @limiter.limit("15/minute")
    async def gemini_verify(req: GeminiRequest, request: Request):
        """Legacy endpoint — calls Groq without live news context."""
        groq_key = os.getenv("GROQ_API_KEY", "")
        if not groq_key:
            raise HTTPException(503, "AI verification not configured. Set GROQ_API_KEY env var.")

        text = req.text.strip()[:3000]
        if len(text) < 10:
            raise HTTPException(400, "Text too short for verification")

        result = await _call_groq(AI_VERIFY_PROMPT_SIMPLE.format(text=text))
        if not result:
            raise HTTPException(502, "AI verification failed")

        return {**result, "available": True}

    # ── GNews Web Verification Endpoint ──
    GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")

    class GNewsRequest(BaseModel):
        text: str

    @app.post("/api/v1/gnews-search")
    @limiter.limit("15/minute")
    async def gnews_search(req: GNewsRequest, request: Request):
        if not GNEWS_API_KEY:
            raise HTTPException(503, "GNews API not configured. Set GNEWS_API_KEY env var.")

        text = req.text.strip()
        if len(text) < 10:
            raise HTTPException(400, "Text too short for search")

        # Extract keywords for search
        from utils import extract_keywords
        keywords = extract_keywords(text, max_keywords=5)
        if not keywords:
            keywords = " ".join(text.split()[:5])

        try:
            from backend.http_client import get_client
            params = {
                "q": keywords,
                "apikey": GNEWS_API_KEY,
                "lang": "en",
                "max": 10,
                "sortby": "relevance"
            }
            resp = await get_client().get("https://gnews.io/api/v4/search", params=params)

            if resp.status_code != 200:
                raise HTTPException(502, f"GNews API returned status {resp.status_code}")

            data = resp.json()
            articles = data.get("articles", []) if isinstance(data, dict) else []

            # Filter quality articles
            quality = []
            for a in articles:
                if a.get("title") and a.get("source", {}).get("name") and a.get("url"):
                    quality.append({
                        "title": a["title"],
                        "source": a["source"]["name"],
                        "url": a["url"],
                        "publishedAt": a.get("publishedAt", ""),
                    })

            # Calculate web corroboration score
            trusted = ['reuters', 'apnews', 'bbc', 'nytimes', 'washingtonpost',
                       'theguardian', 'bloomberg', 'wsj', 'cnn', 'npr', 'pbs',
                       'abcnews', 'cbsnews', 'nbcnews', 'usatoday', 'associated press']
            trusted_count = sum(1 for a in quality if any(t in a["source"].lower() for t in trusted))
            total = len(quality)

            if total == 0:
                web_score = 0.3  # No articles found — uncertain
            elif trusted_count >= 3:
                web_score = 0.9  # Strong corroboration
            elif trusted_count >= 1:
                web_score = 0.7  # Some trusted sources
            elif total >= 3:
                web_score = 0.5  # Articles found but not from trusted sources
            else:
                web_score = 0.4  # Minimal coverage

            return {
                "web_score": web_score,
                "total_articles": total,
                "trusted_count": trusted_count,
                "articles": quality[:5],  # Return top 5
                "keywords": keywords,
                "available": True
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"GNews search failed: {e}")
            raise HTTPException(502, "GNews search failed. Please try again.")

    @app.post("/api/v1/batch")
    @limiter.limit("10/minute")
    async def analyze_batch(request: Request, batch: BatchRequest):
        if not MODEL_LOADED:
            raise HTTPException(503, "Model not loaded")
        if len(batch.articles) > 50:
            raise HTTPException(400, "Maximum 50 articles per batch")

        results = []
        for article in batch.articles:
            try:
                text = article.safe_text  # H6 FIX: bound input size
                cleaned = clean_text(text)
                tfidf_features = tfidf.transform([cleaned])
                meta = compute_meta_features(re.sub(r'\s+', ' ', text).strip()).reshape(1, -1)
                meta_scaled = scaler.transform(meta)
                features = hstack([tfidf_features, meta_scaled])
                proba = model.predict_proba(features)[0]
                real_prob, fake_prob = float(proba[1]), float(proba[0])
                results.append({
                    "id": article.id, "prediction": "REAL" if real_prob >= MODEL_THRESHOLD else "FAKE",
                    "confidence": max(real_prob, fake_prob) * 100,
                    "real_probability": real_prob, "fake_probability": fake_prob,
                    "red_flag_score": detect_fake_news_red_flags(text)
                })
            except Exception as e:
                logger.error(f"Batch analysis error for article {article.id}: {e}")
                results.append({"id": article.id, "error": "Analysis failed for this article"})

        return {"total": len(batch.articles), "processed": len(results),
                "results": results, "timestamp": datetime.now().isoformat()}

    @app.get("/api/v1/user/stats")
    async def get_user_stats(request: Request):
        """Get dashboard stats for the authenticated user."""
        user_id = _get_user_from_token(request)
        if not user_id:
            raise HTTPException(401, "Not authenticated")
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
            # ── Global stats (all users combined) ──
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

    @app.get("/api/v1/user/history")
    async def get_user_history(request: Request, page: int = 1, limit: int = 25, filter: str = "all"):
        """Get paginated analysis history for the authenticated user."""
        user_id = _get_user_from_token(request)
        if not user_id:
            raise HTTPException(401, "Not authenticated")
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

    # ── URL Fetch Endpoint (Tier 2.2) — 3-Tier Extraction ──
    class FetchUrlRequest(BaseModel):
        url: str

    def _extract_article_from_html(html: str) -> dict:
        """
        Given raw HTML, extract article text using BeautifulSoup.
        Returns dict with 'text', 'title', 'word_count'.
        """
        from bs4 import BeautifulSoup
        import re as _re

        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()

        # Remove noise tags
        NOISE_TAGS = [
            "script", "style", "nav", "footer", "header", "aside",
            "form", "iframe", "noscript", "svg", "figure", "figcaption",
            "button", "input", "select", "textarea", "label",
        ]
        for tag in NOISE_TAGS:
            for el in soup.find_all(tag):
                el.decompose()

        # Remove ad/noise elements by class/id
        AD_PATTERNS = _re.compile(
            r'(ads?[-_]|advert|banner|sidebar|widget|comment|social|share|'
            r'related|popular|trending|newsletter|subscribe|signup|sign-up|'
            r'cookie|consent|popup|modal|promo|sponsor|recommendation|'
            r'breadcrumb|pagination|menu|toolbar|footer|masthead|'
            r'disclaimer|copyright)',
            _re.IGNORECASE
        )
        to_remove = []
        for el in soup.find_all(True):
            if el.attrs is None:
                continue
            el_class = " ".join(el.get("class") or [])
            el_id = el.get("id") or ""
            if AD_PATTERNS.search(el_class) or AD_PATTERNS.search(el_id):
                to_remove.append(el)
        for el in to_remove:
            el.decompose()

        # Find article container: <article> > <main> > content class patterns
        article_container = None
        article_tag = soup.find("article")
        if article_tag:
            article_container = article_tag
        if not article_container:
            main_tag = soup.find("main")
            if main_tag:
                article_container = main_tag
        if not article_container:
            CONTENT_PATTERNS = _re.compile(
                r'(article[-_]?body|article[-_]?content|post[-_]?body|post[-_]?content|'
                r'entry[-_]?content|story[-_]?body|story[-_]?content|'
                r'content[-_]?body|main[-_]?content|page[-_]?content)',
                _re.IGNORECASE
            )
            for el in soup.find_all("div"):
                if el.attrs is None:
                    continue
                el_class = " ".join(el.get("class") or [])
                el_id = el.get("id") or ""
                if CONTENT_PATTERNS.search(el_class) or CONTENT_PATTERNS.search(el_id):
                    article_container = el
                    break

        # Extract paragraphs
        source = article_container if article_container else soup.body or soup
        paragraphs = source.find_all("p")

        BOILERPLATE_KW = [
            "cookie", "subscribe", "sign up", "newsletter",
            "copyright", "all rights reserved", "terms of",
            "privacy policy", "click here", "read more",
            "advertisement", "sponsored", "login", "register",
        ]
        clean_paragraphs = []
        for p in paragraphs:
            text = p.get_text(separator=" ", strip=True)
            if len(text) < 40:
                continue
            lower = text.lower()
            if any(kw in lower for kw in BOILERPLATE_KW):
                continue
            clean_paragraphs.append(text)

        article_text = " ".join(clean_paragraphs[:80])
        return {"text": article_text, "title": title, "word_count": len(article_text.split())}

    @app.post("/api/v1/fetch-url")
    @limiter.limit("10/minute")
    async def fetch_url(req: FetchUrlRequest, request: Request):
        """Fetch and extract article text from a URL using 3-tier extraction."""
        url = req.url.strip()
        if not url.startswith(("http://", "https://")):
            raise HTTPException(400, "Invalid URL — must start with http:// or https://")

        # C5 FIX: SSRF protection — block private/internal/metadata IPs
        try:
            from backend.ssrf import validate_url
            validate_url(url)
        except ValueError as e:
            logger.warning(f"SSRF blocked: {url} — {e}")
            raise HTTPException(403, "This URL is not allowed for security reasons")

        # ── TIER 1: newspaper4k (fast, purpose-built for news articles) ──
        # SSRF: fetch the HTML ourselves via safe_get (which re-validates every
        # redirect hop) and hand it to newspaper via input_html, so newspaper never
        # issues its own redirect-following request to a possibly-internal address.
        try:
            from newspaper import Article
            from backend.http_client import get_client
            from backend.ssrf import safe_get
            _t1_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            _t1_resp = await safe_get(get_client(), url, headers=_t1_headers)
            _t1_resp.raise_for_status()
            article = Article(url)
            article.download(input_html=_t1_resp.text)
            article.parse()
            if article.text and len(article.text.split()) >= 30:
                logger.info(f"URL extraction via newspaper4k: {len(article.text.split())} words from {url}")
                return {
                    "text": article.text[:15000],
                    "title": article.title or "",
                    "word_count": len(article.text.split()),
                    "url": url,
                    "extraction_method": "newspaper4k",
                }
        except Exception as e:
            logger.info(f"newspaper4k failed for {url}: {e}")

        # ── TIER 2: Playwright headless browser (renders JavaScript) ──
        try:
            from playwright.sync_api import sync_playwright
            from backend.ssrf import validate_url as _validate_url

            def _ssrf_route_guard(route):
                # SSRF: re-validate every top-level navigation (the initial request
                # AND each redirect hop, which Playwright re-intercepts) so a 30x to
                # an internal IP (e.g. cloud metadata) can't slip past the one-time
                # check above. Non-navigation sub-resources are passed through.
                req = route.request
                if req.is_navigation_request():
                    try:
                        _validate_url(req.url)
                    except ValueError:
                        route.abort()
                        return
                route.continue_()

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()
                page.route("**/*", _ssrf_route_guard)
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(3000)  # Let JS render
                html = page.content()
                browser.close()

            result = _extract_article_from_html(html)
            if result["word_count"] >= 20:
                logger.info(f"URL extraction via Playwright: {result['word_count']} words from {url}")
                return {**result, "url": url, "extraction_method": "playwright"}
        except Exception as e:
            logger.info(f"Playwright failed for {url}: {e}")

        # ── TIER 3: requests + BeautifulSoup (lightweight fallback) ──
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
            }
            from backend.http_client import get_client
            from backend.ssrf import safe_get
            # SSRF-safe fetch: re-validates the target on every redirect hop.
            resp = await safe_get(get_client(), url, headers=headers)
            resp.raise_for_status()

            result = _extract_article_from_html(resp.text)
            if result["word_count"] >= 20:
                logger.info(f"URL extraction via requests+BS4: {result['word_count']} words from {url}")
                return {**result, "url": url, "extraction_method": "beautifulsoup"}
        except httpx.TimeoutException:
            raise HTTPException(504, "URL fetch timed out. The site may be slow or blocking scrapers.")
        except Exception as e:
            logger.warning(f"All extraction tiers failed for {url}: {e}")

        raise HTTPException(422, "Could not extract enough text from this URL. Try pasting the article text directly.")

    # ── Feedback Endpoint (Tier 2.5) ──
    class FeedbackRequest(BaseModel):
        text: str
        model_prediction: str
        user_correction: str
        reason: Optional[str] = None

    def _init_feedback_table():
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
    # _init_feedback_table() is now called in the startup event (startup_load_model)

    @app.post("/api/v1/feedback")
    @limiter.limit("20/minute")
    async def submit_feedback(req: FeedbackRequest, request: Request):
        """Accept user correction on a model prediction for future retraining."""
        if req.model_prediction not in ("REAL", "FAKE") or req.user_correction not in ("REAL", "FAKE"):
            raise HTTPException(400, "model_prediction and user_correction must be REAL or FAKE")
        if len(req.text.strip()) < 20:
            raise HTTPException(400, "Text too short")

        user_id = _get_user_from_token(request)  # Optional — anonymous feedback allowed
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

    # ── §5 Share event (viral loop instrumentation) ──
    class ShareRequest(BaseModel):
        channel: Optional[str] = None  # e.g. "whatsapp", "twitter", "copy"

    @app.post("/api/v1/share")
    @limiter.limit("60/minute")
    async def log_share(req: ShareRequest, request: Request):
        """Record a share action for the viral-coefficient metric.

        Fire-and-forget from the frontend share buttons. Anonymous allowed;
        never fails the caller — a metrics write must not break the UI.
        """
        channel = (req.channel or "unknown").strip().lower()[:32]
        _metrics.log_event(
            _metrics.EVENT_SHARE,
            user_id=_get_user_from_token(request),
            source="web",
            meta={"channel": channel},
        )
        return {"ok": True}

    # ── Admin Dashboard Endpoint (Tier 3.4) ──
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")

    @app.get("/api/v1/admin/stats")
    async def admin_stats(request: Request):
        """Protected admin endpoint — returns global platform stats."""
        import secrets as _secrets
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not ADMIN_SECRET or not _secrets.compare_digest(token, ADMIN_SECRET):
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
                "model_version": MODEL_VERSION,
                "model_metrics": MODEL_METRICS,
                "daily_trend": trend,
                "recent_feedback": recent_feedback,
                "generated_at": datetime.now().isoformat()
            }
        finally:
            conn.close()

    @app.get("/api/v1/admin/metrics")
    async def admin_metrics(request: Request, window_days: int = 30):
        """Protected admin endpoint — §5 growth metrics (activation, D7
        retention, viral coefficient, cost-per-check) over a trailing window."""
        import secrets as _secrets
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not ADMIN_SECRET or not _secrets.compare_digest(token, ADMIN_SECRET):
            raise HTTPException(403, "Admin access required")
        window_days = max(1, min(int(window_days), 365))
        return _metrics.compute_metrics(window_days=window_days)

    # ── Phase 11.2: SEO — Sitemap, robots.txt, Structured Data ──

    @app.get("/sitemap.xml", tags=["SEO"])
    def sitemap_xml():
        """Dynamic XML sitemap listing all verified claim pages for search engines."""
        from backend.claims_db import list_all_claim_hashes
        from fastapi.responses import Response

        base = "https://fake-news-detector-8djq.onrender.com"
        claims = list_all_claim_hashes()

        urls = [
            f'  <url><loc>{base}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>',
            f'  <url><loc>{base}/about</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>',
        ]
        for c in claims:
            date_tag = ""
            if c.get("created_at"):
                date_str = c["created_at"][:10]  # YYYY-MM-DD
                if len(date_str) == 10:
                    date_tag = f"<lastmod>{date_str}</lastmod>"
            urls.append(
                f'  <url><loc>{base}/claim/{c["hash"]}</loc>{date_tag}'
                f'<changefreq>monthly</changefreq><priority>0.7</priority></url>'
            )

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
        return Response(content=xml, media_type="application/xml",
                        headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/robots.txt", tags=["SEO"])
    def robots_txt():
        """Serve robots.txt directing crawlers to the sitemap."""
        from fastapi.responses import PlainTextResponse
        base = "https://fake-news-detector-8djq.onrender.com"
        content = f"""User-agent: *
Allow: /
Allow: /claim/
Allow: /about
Disallow: /api/
Disallow: /dashboard
Disallow: /settings
Disallow: /batch

Sitemap: {base}/sitemap.xml
"""
        return PlainTextResponse(content=content,
                                 headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/api/v1/claim/{claim_hash}/ld-json", tags=["SEO"])
    def claim_structured_data(claim_hash: str):
        """Return ClaimReview JSON-LD structured data for Google Fact Check Tools."""
        from backend.claims_db import get_seo_claim

        claim = get_seo_claim(claim_hash)
        if not claim:
            raise HTTPException(404, "Claim not found")

        verdict = claim.get("verdict", "UNVERIFIABLE")
        confidence = claim.get("confidence", 0)
        text = claim.get("claim_text", claim.get("text", ""))
        analysis = claim.get("analysis", "")
        base = "https://fake-news-detector-8djq.onrender.com"

        # Map verdict to ClaimReview alternateName
        rating_map = {
            "LIKELY_TRUE": {"name": "True", "value": 4, "best": 5, "worst": 1},
            "LIKELY_FALSE": {"name": "False", "value": 1, "best": 5, "worst": 1},
            "MIXED": {"name": "Mixture", "value": 3, "best": 5, "worst": 1},
            "UNVERIFIABLE": {"name": "Unverifiable", "value": 2, "best": 5, "worst": 1},
        }
        rating = rating_map.get(verdict, rating_map["UNVERIFIABLE"])

        ld_json = {
            "@context": "https://schema.org",
            "@type": "ClaimReview",
            "url": f"{base}/claim/{claim_hash}",
            "claimReviewed": text[:500],
            "author": {
                "@type": "Organization",
                "name": "VerifAI",
                "url": base,
            },
            "reviewRating": {
                "@type": "Rating",
                "ratingValue": rating["value"],
                "bestRating": rating["best"],
                "worstRating": rating["worst"],
                "alternateName": rating["name"],
            },
            "itemReviewed": {
                "@type": "Claim",
                "name": text[:200],
                "appearance": {
                    "@type": "CreativeWork",
                    "url": f"{base}/claim/{claim_hash}",
                },
            },
        }
        return ld_json

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
    if FASTAPI_AVAILABLE:
        import uvicorn
        port = int(os.environ.get("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        print("FastAPI not installed.")
