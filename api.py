"""
FastAPI REST API for Fake News Detection — Production Server
Serves both the API endpoints AND the static frontend.

Run locally:  uvicorn api:app --reload
Deploy:       Render / Railway / Fly.io
"""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

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
    from fastapi.responses import FileResponse
    from pydantic import BaseModel
    from typing import Optional, List
    import joblib
    import re
    from datetime import datetime, timedelta
    import bcrypt
    import secrets
    import sqlite3
    from slowapi import Limiter, _rate_limit_exceeded_handler
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

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Database Layer (PostgreSQL in production, SQLite locally) ──
    BASE_DIR = Path(__file__).resolve().parent
    DATABASE_URL = os.environ.get("DATABASE_URL")
    USE_POSTGRES = False

    if DATABASE_URL:
        try:
            import psycopg2
            USE_POSTGRES = True
            print("[OK] PostgreSQL mode — persistent cloud database")
        except ImportError:
            print("[WARN] psycopg2 not installed, falling back to SQLite")

    if not USE_POSTGRES:
        print("[OK] SQLite mode — local development")

    # Connection pool for PostgreSQL (reuse connections instead of opening/closing each request)
    _pg_pool = None

    if USE_POSTGRES:
        try:
            from psycopg2 import pool as pg_pool
            url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
            _pg_pool = pg_pool.SimpleConnectionPool(minconn=1, maxconn=10, dsn=url)
            print(f"[OK] PostgreSQL connection pool created (1-10 connections)")
        except Exception as e:
            print(f"[WARN] Failed to create connection pool: {e}")
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
            print("[OK] Migrated sessions table: added expires_at column")
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

    class PredictionResponse(BaseModel):
        prediction: str
        confidence: float
        confidence_tier: str
        real_probability: float
        fake_probability: float
        red_flag_score: float
        input_quality: str = "sufficient"
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
            if user[4] != "bcrypt" and not user[3].startswith("$2b$"):
                new_hash = _hash_password(req.password)
                c.execute(
                    f"UPDATE users SET password_hash = {ph()}, salt = {ph()} WHERE id = {ph()}",
                    (new_hash, "bcrypt", user[0])
                )
                print(f"[OK] Auto-upgraded password hash to bcrypt for user {user[0]}")

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
                f"SELECT u.id, u.name, u.email FROM users u JOIN sessions s ON s.user_id = u.id WHERE s.token = {ph()}",
                (token,)
            )
            user = c.fetchone()
            if not user:
                raise HTTPException(401, "Invalid session")
            return {"id": user[0], "name": user[1], "email": user[2]}
        finally:
            conn.close()

    @app.post("/api/v1/auth/logout")
    async def logout(request: Request):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token:
            conn = get_db()
            c = conn.cursor()
            c.execute(f"DELETE FROM sessions WHERE token = {ph()}", (token,))
            conn.commit()
            conn.close()
        return {"ok": True}

    # ── Load ML Model ──
    MODEL_DIR = BASE_DIR / "models"
    try:
        model = joblib.load(MODEL_DIR / "model.joblib")
        tfidf = joblib.load(MODEL_DIR / "tfidf.joblib")
        scaler = joblib.load(MODEL_DIR / "scaler.joblib")
        MODEL_LOADED = True
        print("[OK] Model loaded successfully.")
    except Exception as e:
        MODEL_LOADED = False
        print(f"[WARN] Model could not be loaded: {e}")

    # ── Helper Functions ──
    # clean_text, compute_meta_features (extract_single), and detect_fake_news_red_flags
    # are now imported from utils.py, meta_features.py, and enhanced_features.py respectively.
    # This ensures the API uses the EXACT same preprocessing as the training pipeline.

    # ── ML API Endpoints ──
    @app.get("/api/v1/info")
    async def api_info():
        return {
            "name": "Fake News Detector API", "version": "5.0",
            "status": "operational" if MODEL_LOADED else "model_not_loaded",
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy" if MODEL_LOADED else "unhealthy", "model_loaded": MODEL_LOADED,
                "db_mode": "postgresql" if USE_POSTGRES else "sqlite",
                "timestamp": datetime.now().isoformat()}

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
        prediction = "FAKE" if fake_prob > 0.5 else "REAL"
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
            confidence_tier = "Leaning Real" if prediction == "REAL" else "Leaning Fake"
        elif confidence >= 50:
            confidence_tier = "Suspicious"
        else:
            confidence_tier = "Inconclusive"

        # Save analysis to DB if user is authenticated
        user_id = _get_user_from_token(request)
        if user_id:
            preview = text[:200].replace("'", "")
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute(
                    f"INSERT INTO analyses (user_id, text_preview, prediction, confidence, real_prob, fake_prob, red_flag_score) VALUES ({ph(7)})",
                    (user_id, preview, prediction, confidence, real_prob, fake_prob, red_flag_score)
                )
                conn.commit()
                print(f"[OK] Analysis saved for user {user_id}: {prediction} ({confidence_tier})")
            except Exception as e:
                print(f"[ERR] Failed to save analysis: {e}")
                conn.rollback()
            finally:
                conn.close()
        else:
            print("[WARN] No user_id found, analysis NOT saved")

        return PredictionResponse(
            prediction=prediction, confidence=confidence,
            confidence_tier=confidence_tier, input_quality=input_quality,
            real_probability=real_prob, fake_probability=fake_prob,
            red_flag_score=red_flag_score, timestamp=datetime.now().isoformat()
        )

    # ── AI Verification Endpoint (Groq — free, no billing required) ──

    AI_VERIFY_PROMPT = """You are an expert media analyst. Evaluate this article for credibility.

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

    class GeminiRequest(BaseModel):
        text: str

    @app.post("/api/v1/gemini-verify")
    @limiter.limit("15/minute")
    async def gemini_verify(req: GeminiRequest, request: Request):
        groq_key = os.getenv("GROQ_API_KEY", "")
        if not groq_key:
            raise HTTPException(503, "AI verification not configured. Set GROQ_API_KEY env var.")

        text = req.text.strip()[:3000]
        if len(text) < 10:
            raise HTTPException(400, "Text too short for verification")

        # Groq API (OpenAI-compatible REST endpoint)
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are an expert media analyst and fact-checker."},
                {"role": "user", "content": AI_VERIFY_PROMPT.format(text=text)}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload, timeout=15
            )

            if resp.status_code != 200:
                error_msg = resp.json().get("error", {}).get("message", resp.text[:200])
                print(f"[ERR] Groq API error {resp.status_code}: {error_msg}")
                raise HTTPException(502, f"AI verification failed: {error_msg}")

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

            # Convert to credibility score (0.0 - 1.0)
            score_map = {"HIGH": 0.85, "MEDIUM": 0.5, "LOW": 0.2}
            credibility_score = score_map.get(credibility, 0.5)

            return {
                "credibility": credibility,
                "credibility_score": credibility_score,
                "confidence": confidence,
                "verdict": verdict,
                "analysis": analysis,
                "available": True
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"[ERR] AI verification failed: {e}")
            raise HTTPException(502, f"AI verification failed: {str(e)}")

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
            print(f"[ERR] GNews search failed: {e}")
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
