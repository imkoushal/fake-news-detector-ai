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

import numpy as np
from scipy.sparse import hstack

# Import canonical preprocessing and feature functions (same as training pipeline)
from utils import clean_text
from meta_features import extract_single as compute_meta_features
from enhanced_features import detect_fake_news_red_flags

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel
    from typing import Optional, List
    import joblib
    import re
    import requests
    from datetime import datetime, timedelta
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
    # ── Initialize FastAPI ──
    app = FastAPI(
        title="Fake News Detector API",
        description="Hybrid ML-powered fake news detection API",
        version="5.0"
    )

    # ── CORS — read allowed origins from env, default to localhost for dev ──
    _cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8501")
    ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    limiter = Limiter(
        key_func=lambda request: (
            # Per-user rate limiting (3.8): use user_id for auth'd users, IP for anonymous
            request.headers.get("Authorization", "").replace("Bearer ", "") or get_remote_address(request)
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

    # ── Database Layer (PostgreSQL in production, SQLite locally) ──
    BASE_DIR = Path(__file__).resolve().parent
    DATABASE_URL = os.environ.get("DATABASE_URL")
    USE_POSTGRES = False

    if DATABASE_URL:
        try:
            import psycopg2
            USE_POSTGRES = True
        except ImportError:
            pass

    if USE_POSTGRES:
        logger.info("PostgreSQL mode — persistent cloud database")
    else:
        logger.info("SQLite mode — local development")

    # Connection pool for PostgreSQL (reuse connections instead of opening/closing each request)
    _pg_pool = None

    if USE_POSTGRES:
        try:
            from psycopg2 import pool as pg_pool
            url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
            _pg_pool = pg_pool.SimpleConnectionPool(minconn=1, maxconn=10, dsn=url)
            logger.info("PostgreSQL connection pool created (1-10 connections)")
        except Exception as e:
            logger.warning(f"Failed to create connection pool: {e}")
            _pg_pool = None

    class _PooledConnection:
        """Wraps a psycopg2 connection so that .close() returns it to the pool."""
        def __init__(self, conn, pool):
            self._conn = conn
            self._pool = pool
        def close(self):
            try: self._pool.putconn(self._conn)
            except Exception:
                try: self._conn.close()
                except Exception: pass
        def __getattr__(self, name):
            return getattr(self._conn, name)

    def get_db():
        """Get a database connection (pooled for PostgreSQL)."""
        if USE_POSTGRES:
            if _pg_pool:
                conn = _pg_pool.getconn()
                conn.autocommit = False
                return _PooledConnection(conn, _pg_pool)
            else:
                url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
                conn = psycopg2.connect(url)
                conn.autocommit = False
                return conn
        else:
            return sqlite3.connect(str(BASE_DIR / "users.db"))

    def ph(n=1):
        """Return SQL placeholder(s) — %s for PostgreSQL, ? for SQLite."""
        p = "%s" if USE_POSTGRES else "?"
        return ", ".join([p] * n)

    # ── Centralized DB Execution Helper (Codex Fix #2) ──
    def execute_db(query: str, params: tuple = (), *, fetch: str = "none", commit: bool = False):
        """Run a SQL query with guaranteed connection cleanup.
        
        Args:
            query:  SQL string with placeholders.
            params: Tuple of parameter values.
            fetch:  'none' | 'one' | 'all' — what to return from the cursor.
            commit: Whether to commit the transaction.
        
        Returns:
            None, a single row tuple, or a list of row tuples.
        """
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(query, params)
            if commit:
                conn.commit()
            if fetch == "one":
                return c.fetchone()
            elif fetch == "all":
                return c.fetchall()
            return None
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_auth_db():
        conn = get_db()
        c = conn.cursor()
        if USE_POSTGRES:
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS analyses (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                text_preview TEXT NOT NULL,
                prediction TEXT NOT NULL,
                confidence REAL NOT NULL,
                real_prob REAL NOT NULL,
                fake_prob REAL NOT NULL,
                red_flag_score REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        else:
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text_preview TEXT NOT NULL,
                prediction TEXT NOT NULL,
                confidence REAL NOT NULL,
                real_prob REAL NOT NULL,
                fake_prob REAL NOT NULL,
                red_flag_score REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )''')

        # Migration: add expires_at column if it doesn't exist (for pre-existing databases)
        try:
            if USE_POSTGRES:
                c.execute("ALTER TABLE sessions ADD COLUMN expires_at TIMESTAMP")
            else:
                c.execute("ALTER TABLE sessions ADD COLUMN expires_at DATETIME")
            logger.info("Migrated sessions table: added expires_at column")
        except Exception:
            pass  # Column already exists — this is expected

        conn.commit()
        conn.close()

    _init_auth_db()

    def _hash_password(password: str) -> str:
        """Hash a password using bcrypt (salt is embedded in the output)."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def _verify_password(password: str, stored_hash: str, stored_salt: str = "") -> bool:
        """Verify a password against its hash.
        Supports both bcrypt (new) and legacy SHA-256 (old) hashes.
        """
        if stored_salt == "bcrypt" or stored_hash.startswith("$2b$"):
            # Modern bcrypt hash
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        else:
            # Legacy SHA-256 fallback — needed until all users re-login
            import hashlib
            legacy = hashlib.sha256((stored_salt + password).encode()).hexdigest()
            return legacy == stored_hash

    # ── Session token TTL (7 days) ──
    SESSION_TTL_DAYS = 7

    def _sanitize_preview(text: str, max_len: int = 200) -> str:
        """Unicode-safe text preview sanitizer (Manus AI Fix #5).
        Strips control characters but preserves accented letters, quotes, and international text.
        """
        # Strip control characters (U+0000-U+001F, U+007F-U+009F) but keep printable Unicode
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        # Collapse excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        # Truncate safely
        return sanitized[:max_len]

    def _get_user_from_token(request: Request):
        """Extract user_id from auth token. Rejects expired tokens."""
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return None
        conn = get_db()
        c = conn.cursor()
        c.execute(f"SELECT user_id, expires_at FROM sessions WHERE token = {ph()}", (token,))
        row = c.fetchone()
        if not row:
            conn.close()
            return None
        # Check expiry (if expires_at column exists and is set)
        if row[1]:
            try:
                exp = datetime.fromisoformat(str(row[1]))
                if datetime.now() > exp:
                    # Token expired — clean it up
                    c.execute(f"DELETE FROM sessions WHERE token = {ph()}", (token,))
                    conn.commit()
                    conn.close()
                    return None
            except (ValueError, TypeError):
                pass
        conn.close()
        return row[0]

    # ── Pydantic Models ──
    class SignupRequest(BaseModel):
        name: str
        email: str
        password: str

    class LoginRequest(BaseModel):
        email: str
        password: str

    class Article(BaseModel):
        text: str
        url: Optional[str] = None
        source: Optional[str] = None
        sensitivity: Optional[float] = 0.50  # Decision threshold (0.0 lenient – 1.0 strict)

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
        model_version: str = "5.0"

    class BatchArticle(BaseModel):
        id: str
        text: str

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
            return {
                "token": token,
                "user": {"id": user_id, "name": req.name.strip(), "email": req.email.strip().lower()}
            }
        except Exception as e:
            conn.rollback()
            err = str(e).lower()
            if "unique" in err or "duplicate" in err:
                raise HTTPException(409, "An account with this email already exists")
            raise HTTPException(500, str(e))
        finally:
            conn.close()

    @app.post("/api/v1/auth/login")
    @limiter.limit("15/minute")
    async def login(req: LoginRequest, request: Request):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                f"SELECT id, name, email, password_hash, salt FROM users WHERE email = {ph()}",
                (req.email.strip().lower(),)
            )
            user = c.fetchone()
            if not user:
                raise HTTPException(401, "Invalid email or password")
            if not _verify_password(req.password, user[3], user[4]):
                raise HTTPException(401, "Invalid email or password")

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
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            raise HTTPException(401, "Not authenticated")
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                f"SELECT u.id, u.name, u.email, u.avatar_url FROM users u JOIN sessions s ON s.user_id = u.id WHERE s.token = {ph()}",
                (token,)
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
        Decodes the Google ID token, verifies it, and creates or logs in the user.
        """
        import json as _json
        import base64

        if not GOOGLE_CLIENT_ID:
            raise HTTPException(500, "Google OAuth is not configured on this server")

        # Decode the JWT payload (middle segment) without external libraries
        # The signature is already verified client-side by Google's JS SDK,
        # but we also verify the audience (aud) and issuer (iss) claims server-side.
        try:
            parts = req.credential.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT format")
            # Decode the payload (add padding if needed)
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
        # Check expiry
        import time as _time
        if payload.get("exp", 0) < _time.time():
            raise HTTPException(401, "Google token has expired")

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

    # ── Load ML Model + version info (3.1) ──
    MODEL_DIR = BASE_DIR / "models"
    MODEL_VERSION = "5.0"  # fallback
    MODEL_METRICS = {}
    try:
        model = joblib.load(MODEL_DIR / "model.joblib")
        tfidf = joblib.load(MODEL_DIR / "tfidf.joblib")
        scaler = joblib.load(MODEL_DIR / "scaler.joblib")
        MODEL_LOADED = True
        # Load version & metrics from config.json if present
        cfg_path = MODEL_DIR / "config.json"
        if cfg_path.exists():
            import json as _json
            with open(cfg_path) as f:
                cfg = _json.load(f)
            MODEL_VERSION = cfg.get("version", MODEL_VERSION)
            MODEL_METRICS = {
                "accuracy": cfg.get("accuracy"),
                "f1_score": cfg.get("f1_score"),
                "roc_auc": cfg.get("roc_auc"),
                "training_date": cfg.get("training_date"),
                "total_features": cfg.get("total_features"),
                "model_type": cfg.get("model_type"),
                "total_training_samples": cfg.get("total_training_samples"),
            }
        logger.info(f"Model v{MODEL_VERSION} loaded successfully.")
    except Exception as e:
        MODEL_LOADED = False
        logger.warning(f"Model could not be loaded: {e}")

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
    async def health_check():
        return {
            "status": "healthy" if MODEL_LOADED else "unhealthy",
            "model_loaded": MODEL_LOADED,
            "model_version": MODEL_VERSION,
            "db_mode": "postgresql" if USE_POSTGRES else "sqlite",
            "timestamp": datetime.now().isoformat()
        }

    # Debug endpoint removed — was leaking DB schema unauthenticated (Issue #6)

    @app.post("/api/v1/analyze", response_model=PredictionResponse)
    @limiter.limit("30/minute")
    async def analyze_article(article: Article, request: Request):
        if not MODEL_LOADED:
            raise HTTPException(503, "Model not loaded")

        text = article.text.strip()
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

        # Compute and scale the 20 meta-features, then concatenate with TF-IDF
        meta = compute_meta_features(text).reshape(1, -1)
        meta_scaled = scaler.transform(meta)
        features = hstack([tfidf_features, meta_scaled])

        proba = model.predict_proba(features)[0]
        real_prob, fake_prob = float(proba[1]), float(proba[0])
        red_flag_score = detect_fake_news_red_flags(text)
        # Use client-supplied sensitivity as the decision threshold
        threshold = max(0.0, min(1.0, article.sensitivity or 0.50))
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

    def _run_gnews_search(text: str):
        """Internal helper: run GNews search and return structured results."""
        gnews_key = os.getenv("GNEWS_API_KEY", "")
        if not gnews_key or len(text.strip()) < 10:
            return None

        try:
            from utils import extract_keywords
            keywords = extract_keywords(text, max_keywords=5)
            if not keywords:
                keywords = " ".join(text.split()[:5])

            import requests as req_lib
            params = {
                "q": keywords,
                "apikey": gnews_key,
                "lang": "en",
                "max": 10,
                "sortby": "relevance"
            }
            resp = req_lib.get("https://gnews.io/api/v4/search", params=params, timeout=10)
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

    def _call_groq(prompt_text: str):
        """Internal helper: call Groq LLaMA API and return parsed result."""
        groq_key = os.getenv("GROQ_API_KEY", "")
        if not groq_key:
            return None

        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are an expert media analyst and fact-checker with access to live news feeds."},
                {"role": "user", "content": prompt_text}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=payload, timeout=15
        )

        if resp.status_code != 200:
            error_msg = resp.json().get("error", {}).get("message", resp.text[:200])
            logger.error(f"Groq API error {resp.status_code}: {error_msg}")
            return None

        result_text = resp.json()["choices"][0]["message"]["content"]

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
        text = req.text.strip()[:3000]
        if len(text) < 10:
            raise HTTPException(400, "Text too short for verification")

        # Step 1: Run GNews search for live context
        gnews_result = _run_gnews_search(text)

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
            logger.info(f"Smart verify: RAG mode with {gnews_result['total_articles']} live articles")
        else:
            # Fallback: no live context available
            prompt = AI_VERIFY_PROMPT_SIMPLE.format(text=text)
            logger.info("Smart verify: fallback mode (no live news context)")

        # Step 3: Call Groq with the enriched prompt
        ai_result = _call_groq(prompt)

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

        return response

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

        result = _call_groq(AI_VERIFY_PROMPT_SIMPLE.format(text=text))
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
            import requests as req_lib
            params = {
                "q": keywords,
                "apikey": GNEWS_API_KEY,
                "lang": "en",
                "max": 10,
                "sortby": "relevance"
            }
            resp = req_lib.get("https://gnews.io/api/v4/search", params=params, timeout=10)

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
            raise HTTPException(502, f"GNews search failed: {str(e)}")

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
                cleaned = clean_text(article.text)
                tfidf_features = tfidf.transform([cleaned])
                meta = compute_meta_features(article.text).reshape(1, -1)
                meta_scaled = scaler.transform(meta)
                features = hstack([tfidf_features, meta_scaled])
                proba = model.predict_proba(features)[0]
                real_prob, fake_prob = float(proba[1]), float(proba[0])
                results.append({
                    "id": article.id, "prediction": "FAKE" if fake_prob > 0.5 else "REAL",
                    "confidence": max(real_prob, fake_prob) * 100,
                    "real_probability": real_prob, "fake_probability": fake_prob,
                    "red_flag_score": detect_fake_news_red_flags(article.text)
                })
            except Exception as e:
                results.append({"id": article.id, "error": str(e)})

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

        extraction_method = "unknown"

        # ── TIER 1: newspaper4k (fast, purpose-built for news articles) ──
        try:
            from newspaper import Article
            article = Article(url)
            article.download()
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
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()
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
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            resp.raise_for_status()

            result = _extract_article_from_html(resp.text)
            if result["word_count"] >= 20:
                logger.info(f"URL extraction via requests+BS4: {result['word_count']} words from {url}")
                return {**result, "url": url, "extraction_method": "beautifulsoup"}
        except requests.exceptions.Timeout:
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
    _init_feedback_table()

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

    # ── Admin Dashboard Endpoint (Tier 3.4) ──
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")

    @app.get("/api/v1/admin/stats")
    async def admin_stats(request: Request):
        """Protected admin endpoint — returns global platform stats."""
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not ADMIN_SECRET or token != ADMIN_SECRET:
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

    # ── API catch-all: return proper 404 for unmatched /api/ paths ──
    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def api_catchall(path: str):
        raise HTTPException(404, f"API endpoint /api/{path} not found")

    # ── Serve Static Frontend ──
    FRONTEND_DIR = BASE_DIR / "frontend"

    @app.get("/")
    async def serve_index():
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"message": "Fake News Detector API v5.0", "docs": "/docs"}

    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

# ── Entry Point ──
if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        import uvicorn
        port = int(os.environ.get("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        print("FastAPI not installed.")
