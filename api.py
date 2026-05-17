"""
FastAPI REST API for Fake News Detection — Production Server
Serves both the API endpoints AND the static frontend.

Run locally:  uvicorn api:app --reload
Deploy:       Render / Railway / Fly.io
"""
import os
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from pydantic import BaseModel
    from typing import Optional, List
    import joblib
    import re
    from datetime import datetime
    import hashlib
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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

    def get_db():
        """Get a database connection."""
        if USE_POSTGRES:
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
                FOREIGN KEY(user_id) REFERENCES users(id)
            )''')
        conn.commit()
        conn.close()

    _init_auth_db()

    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((salt + password).encode()).hexdigest()

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
        real_probability: float
        fake_probability: float
        red_flag_score: float
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

        salt = secrets.token_hex(16)
        pw_hash = _hash_password(req.password, salt)

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
            c.execute(f"INSERT INTO sessions (token, user_id) VALUES ({ph(2)})", (token, user_id))
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
            if _hash_password(req.password, user[4]) != user[3]:
                raise HTTPException(401, "Invalid email or password")

            token = secrets.token_urlsafe(32)
            c.execute(f"INSERT INTO sessions (token, user_id) VALUES ({ph(2)})", (token, user[0]))
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
        MODEL_LOADED = True
        print("[OK] Model loaded successfully.")
    except Exception as e:
        MODEL_LOADED = False
        print(f"[WARN] Model could not be loaded: {e}")

    # ── Helper Functions ──
    def clean_text(text: str) -> str:
        text = str(text).lower()
        text = re.sub(r'http\S+|www\S+|https\S+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = ' '.join([word for word in text.split() if len(word) > 2])
        return text.strip()

    def detect_red_flags(text: str) -> float:
        red_flags = 0
        text_lower = text.lower()
        if any(w in text_lower for w in ['big pharma', 'mainstream media', 'deep state', 'government coverup']):
            red_flags += 2
        if any(w in text_lower for w in ['doctors dont want you to know', 'miracle cure', 'ancient remedy']):
            red_flags += 3
        if any(w in text_lower for w in ['share before deleted', 'share now', 'censored']):
            red_flags += 2
        if sum(1 for c in text if c.isupper()) / max(len(text), 1) > 0.1:
            red_flags += 1
        if text.count('!') > 5 or text.count('?') > 5:
            red_flags += 1
        return min(red_flags, 10) / 10

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

    @app.post("/api/v1/analyze", response_model=PredictionResponse)
    @limiter.limit("30/minute")
    async def analyze_article(article: Article, request: Request):
        if not MODEL_LOADED:
            raise HTTPException(503, "Model not loaded")
        if len(article.text) < 50:
            raise HTTPException(400, "Article text too short (minimum 50 characters)")

        cleaned = clean_text(article.text)
        features = tfidf.transform([cleaned])
        proba = model.predict_proba(features)[0]
        real_prob, fake_prob = float(proba[1]), float(proba[0])
        red_flag_score = detect_red_flags(article.text)
        prediction = "FAKE" if fake_prob > 0.5 else "REAL"

        return PredictionResponse(
            prediction=prediction, confidence=max(real_prob, fake_prob) * 100,
            real_probability=real_prob, fake_probability=fake_prob,
            red_flag_score=red_flag_score, timestamp=datetime.now().isoformat()
        )

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
                proba = model.predict_proba(tfidf.transform([cleaned]))[0]
                real_prob, fake_prob = float(proba[1]), float(proba[0])
                results.append({
                    "id": article.id, "prediction": "FAKE" if fake_prob > 0.5 else "REAL",
                    "confidence": max(real_prob, fake_prob) * 100,
                    "real_probability": real_prob, "fake_probability": fake_prob,
                    "red_flag_score": detect_red_flags(article.text)
                })
            except Exception as e:
                results.append({"id": article.id, "error": str(e)})

        return {"total": len(batch.articles), "processed": len(results),
                "results": results, "timestamp": datetime.now().isoformat()}

    @app.get("/api/v1/stats")
    async def get_stats():
        return {"total_requests": 0, "requests_today": 0, "message": "Statistics tracking not yet implemented"}

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
