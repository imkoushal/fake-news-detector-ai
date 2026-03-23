<![CDATA["""
FastAPI REST API for Fake News Detection
Run: uvicorn api:app --reload
Docs: http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional, List
import joblib
import re
import os
from datetime import datetime
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

# ─── App Init ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Fake News Detector API",
    description="Hybrid ML-powered fake news detection with prediction confidence scoring",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
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

# ─── Auth ─────────────────────────────────────────────────────────────────────

API_KEYS: dict[str, str] = {
    "demo_key_123": "demo_user",
    "prod_key_456": "production_user",
}

CUSTOM_API_KEY = os.getenv("API_CUSTOM_KEY")
if CUSTOM_API_KEY:
    API_KEYS[CUSTOM_API_KEY] = "custom_user"


def verify_api_key(x_api_key: str = Header(None)) -> str:
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return API_KEYS[x_api_key]


# ─── Model Loading ────────────────────────────────────────────────────────────

MODEL_LOADED = False
model = None
tfidf = None

try:
    model = joblib.load("models/model.joblib")
    tfidf = joblib.load("models/tfidf.joblib")
    MODEL_LOADED = True
except Exception:
    MODEL_LOADED = False


# ─── Schemas ──────────────────────────────────────────────────────────────────

class Article(BaseModel):
    text: str
    url: Optional[str] = None
    source: Optional[str] = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or len(v.strip()) < 10:
            raise ValueError("Text must be at least 10 characters")
        if len(v) > 10000:
            raise ValueError("Text must not exceed 10 000 characters")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    real_probability: float
    fake_probability: float
    red_flag_score: float
    text_length: int
    category: Optional[str] = None
    timestamp: str
    model_version: str = "2.1.0"


class BatchArticle(BaseModel):
    id: str
    text: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Article ID cannot be empty")
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or len(v.strip()) < 10:
            raise ValueError("Text must be at least 10 characters")
        return v


class BatchRequest(BaseModel):
    articles: List[BatchArticle]

    @field_validator("articles")
    @classmethod
    def validate_articles(cls, v: List[BatchArticle]) -> List[BatchArticle]:
        if len(v) == 0:
            raise ValueError("Batch must contain at least 1 article")
        if len(v) > 50:
            raise ValueError("Batch cannot exceed 50 articles")
        return v


# ─── Helpers ──────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+|https\S+", "", text)
    text = re.sub(r"\S+@\S+", "", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = " ".join(w for w in text.split() if len(w) > 2)
    return text.strip()


def detect_red_flags(text: str) -> float:
    flags = 0
    t = text.lower()

    conspiracy = ["big pharma", "mainstream media", "deep state", "government coverup", "they dont want you to know"]
    if any(w in t for w in conspiracy):
        flags += 2

    medical = ["doctors dont want you to know", "miracle cure", "ancient remedy", "big pharma doesnt want"]
    if any(w in t for w in medical):
        flags += 3

    urgency = ["share before deleted", "share now", "censored", "banned video", "they are hiding"]
    if any(w in t for w in urgency):
        flags += 2

    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if caps_ratio > 0.15:
        flags += 1

    if text.count("!") > 5 or text.count("?") > 5:
        flags += 1

    clickbait = ["you wont believe", "this one weird trick", "shocking truth", "what happened next"]
    if any(w in t for w in clickbait):
        flags += 2

    return min(flags, 10) / 10


def _predict(text: str) -> dict:
    """Core prediction logic — returns dict with all result fields."""
    cleaned = clean_text(text)
    features = tfidf.transform([cleaned])
    proba = model.predict_proba(features)[0]

    real_prob = float(proba[0])
    fake_prob = float(proba[1])
    prediction = "FAKE" if fake_prob > 0.5 else "REAL"
    confidence = round(max(real_prob, fake_prob) * 100, 2)
    red_flag_score = detect_red_flags(text)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "real_probability": round(real_prob, 4),
        "fake_probability": round(fake_prob, 4),
        "red_flag_score": round(red_flag_score, 4),
        "text_length": len(text),
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "Fake News Detector API",
        "version": "2.1.0",
        "status": "operational" if MODEL_LOADED else "model_not_loaded",
        "docs": "/docs",
        "endpoints": ["/health", "/api/v1/analyze", "/api/v1/batch", "/api/v1/status", "/api/v1/stats"],
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if MODEL_LOADED else "unhealthy",
        "model_loaded": MODEL_LOADED,
        "timestamp": datetime.now().isoformat(),
        "version": "2.1.0",
    }


@app.get("/api/v1/status")
async def api_status():
    mem_mb = None
    cpu = None
    try:
        import psutil

        mem_mb = round(psutil.Process().memory_info().rss / 1024 / 1024, 2)
        cpu = psutil.cpu_percent()
    except Exception:
        pass

    return {
        "status": "operational" if MODEL_LOADED else "degraded",
        "model_loaded": MODEL_LOADED,
        "memory_usage_mb": mem_mb,
        "cpu_percent": cpu,
        "timestamp": datetime.now().isoformat(),
        "version": "2.1.0",
    }


@app.post("/api/v1/analyze", response_model=PredictionResponse)
@limiter.limit("30/minute")
async def analyze_article(
    request: Request,
    article: Article,
    user: str = Depends(verify_api_key),
):
    if not MODEL_LOADED:
        raise HTTPException(status_code=503, detail="Model not loaded. Run train.py first.")

    if len(article.text.strip()) < 100:
        raise HTTPException(status_code=400, detail="Article text too short (minimum 100 characters)")

    result = _predict(article.text)

    return PredictionResponse(
        **result,
        category=None,
        timestamp=datetime.now().isoformat(),
    )


@app.post("/api/v1/batch")
@limiter.limit("10/minute")
async def analyze_batch(
    request: Request,
    batch: BatchRequest,
    user: str = Depends(verify_api_key),
):
    if not MODEL_LOADED:
        raise HTTPException(status_code=503, detail="Model not loaded")

    results = []
    for article in batch.articles:
        try:
            r = _predict(article.text)
            r["id"] = article.id
            results.append(r)
        except Exception as e:
            results.append({"id": article.id, "error": str(e)})

    return {
        "total": len(batch.articles),
        "processed": len([r for r in results if "error" not in r]),
        "results": results,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/stats")
async def get_stats(user: str = Depends(verify_api_key)):
    return {
        "user": user,
        "total_requests": 0,
        "requests_today": 0,
        "avg_response_time_ms": 0,
        "model_version": "2.1.0",
        "message": "Per-user statistics tracking not yet implemented",
    }


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api:app", host=host, port=port, reload=True)
]]>
