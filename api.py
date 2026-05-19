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
        conn.commit()
        conn.close()

    _init_auth_db()

    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((salt + password).encode()).hexdigest()

    def _get_user_from_token(request: Request):
        """Extract user_id from auth token. Returns user_id or None."""
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return None
        conn = get_db()
        c = conn.cursor()
        c.execute(f"SELECT user_id FROM sessions WHERE token = {ph()}", (token,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

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
        scaler = joblib.load(MODEL_DIR / "scaler.joblib")
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

    def compute_meta_features(text: str) -> list:
        """Compute the 20 linguistic meta-features the stacking model expects."""
        import math
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        words = text.split()
        word_count = max(len(words), 1)
        char_count = max(len(text), 1)

        sentence_count = max(len(sentences), 1)
        avg_sentence_length = word_count / sentence_count
        exclamation_ratio = text.count('!') / char_count
        question_ratio = text.count('?') / char_count
        all_caps_words = sum(1 for w in words if w.isupper() and len(w) > 1)
        all_caps_ratio = all_caps_words / word_count
        title_case_words = sum(1 for w in words if w.istitle())
        title_case_ratio = title_case_words / word_count
        caps_chars = sum(1 for c in text if c.isupper())
        caps_char_ratio = caps_chars / char_count
        unique_words = set(w.lower() for w in words)
        lexical_diversity = len(unique_words) / word_count
        avg_word_length = sum(len(w) for w in words) / word_count
        first_person = sum(1 for w in words if w.lower() in ['i', 'me', 'my', 'mine', 'we', 'us', 'our', 'ours'])
        first_person_ratio = first_person / word_count
        quoted_source_count = text.count('"') // 2 + text.count('\u201c')
        number_count = len(re.findall(r'\d+', text))
        url_count = len(re.findall(r'http[s]?://\S+', text))

        conspiracy_words = ['conspiracy', 'coverup', 'cover-up', 'illuminati', 'deep state', 'new world order', 'big pharma', 'they dont want']
        conspiracy_score = sum(1 for w in conspiracy_words if w in text.lower())

        sensational_words = ['shocking', 'unbelievable', 'incredible', 'horrifying', 'explosive', 'bombshell', 'breaking', 'urgent', 'miracle', 'secret']
        sensationalism_score = sum(1 for w in sensational_words if w in text.lower())

        red_flag_score = detect_red_flags(text)

        # Flesch-Kincaid approximation
        syllable_count = sum(max(1, len(re.findall(r'[aeiouy]+', w.lower()))) for w in words)
        fk_grade = 0.39 * (word_count / sentence_count) + 11.8 * (syllable_count / word_count) - 15.59

        attribution_words = ['according to', 'said', 'reported', 'stated', 'confirmed', 'announced', 'officials say']
        has_attribution = 1.0 if any(w in text.lower() for w in attribution_words) else 0.0

        clickbait_patterns = ['you won\'t believe', 'what happens next', 'this is why', 'the truth about', 'they don\'t want you']
        clickbait_score = sum(1 for p in clickbait_patterns if p in text.lower())

        return [
            sentence_count, avg_sentence_length, word_count, exclamation_ratio,
            question_ratio, all_caps_ratio, title_case_ratio, caps_char_ratio,
            lexical_diversity, avg_word_length, first_person_ratio, quoted_source_count,
            number_count, url_count, conspiracy_score, sensationalism_score,
            red_flag_score, fk_grade, has_attribution, clickbait_score
        ]

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

    @app.get("/api/v1/debug/db")
    async def debug_db():
        """Temporary debug endpoint to check DB status."""
        conn = get_db()
        c = conn.cursor()
        try:
            if USE_POSTGRES:
                c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            else:
                c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in c.fetchall()]
            counts = {}
            for t in tables:
                c.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = c.fetchone()[0]
            return {"db_mode": "postgresql" if USE_POSTGRES else "sqlite", "tables": tables, "row_counts": counts}
        except Exception as e:
            return {"error": str(e)}
        finally:
            conn.close()

    @app.post("/api/v1/analyze", response_model=PredictionResponse)
    @limiter.limit("30/minute")
    async def analyze_article(article: Article, request: Request):
        if not MODEL_LOADED:
            raise HTTPException(503, "Model not loaded")
        if len(article.text) < 50:
            raise HTTPException(400, "Article text too short (minimum 50 characters)")

        try:
            cleaned = clean_text(article.text)
            tfidf_features = tfidf.transform([cleaned])

            # Compute and scale the 20 meta-features, then concatenate with TF-IDF
            import numpy as np
            from scipy.sparse import hstack
            meta = np.array([compute_meta_features(article.text)])
            meta_scaled = scaler.transform(meta)
            features = hstack([tfidf_features, meta_scaled])

            proba = model.predict_proba(features)[0]
            real_prob, fake_prob = float(proba[1]), float(proba[0])
        except Exception as e:
            print(f"[ERR] Prediction failed: {e}")
            raise HTTPException(500, f"Prediction error: {str(e)}")
        red_flag_score = detect_red_flags(article.text)
        prediction = "FAKE" if fake_prob > 0.5 else "REAL"
        confidence = max(real_prob, fake_prob) * 100

        # Save analysis to DB if user is authenticated
        user_id = _get_user_from_token(request)
        if user_id:
            preview = article.text[:200].replace("'", "")
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute(
                    f"INSERT INTO analyses (user_id, text_preview, prediction, confidence, real_prob, fake_prob, red_flag_score) VALUES ({ph(7)})",
                    (user_id, preview, prediction, confidence, real_prob, fake_prob, red_flag_score)
                )
                conn.commit()
                print(f"[OK] Analysis saved for user {user_id}: {prediction}")
            except Exception as e:
                print(f"[ERR] Failed to save analysis: {e}")
                conn.rollback()
            finally:
                conn.close()
        else:
            print("[WARN] No user_id found, analysis NOT saved")

        return PredictionResponse(
            prediction=prediction, confidence=confidence,
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
                tfidf_features = tfidf.transform([cleaned])
                import numpy as np
                from scipy.sparse import hstack
                meta = np.array([compute_meta_features(article.text)])
                meta_scaled = scaler.transform(meta)
                features = hstack([tfidf_features, meta_scaled])
                proba = model.predict_proba(features)[0]
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
