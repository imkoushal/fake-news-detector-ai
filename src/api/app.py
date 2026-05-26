"""
⚠️  DEPRECATED — This modular API rewrite is NOT the production entrypoint.

The production server is the root `api.py` which includes:
  - User authentication (signup/login/logout/sessions)
  - Groq AI verification (/api/v1/gemini-verify)
  - GNews web verification (/api/v1/gnews-search)
  - User history & dashboard stats
  - Feedback collection (/api/v1/feedback)
  - Admin dashboard (/api/v1/admin/stats)
  - Word-level explainability (XAI)

This file exists as a reference for the modular architecture pattern.
DO NOT deploy this file. Use `uvicorn api:app` instead.

Run with: uvicorn src.api.app:app --reload  (DEV ONLY)
"""
import warnings
warnings.warn(
    "src.api.app is DEPRECATED and lacks feature parity with the production api.py. "
    "Use `uvicorn api:app` for the production server.",
    DeprecationWarning,
    stacklevel=2,
)

from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.core.config import settings
from src.core.exceptions import ModelNotLoadedError, PredictionError, ValidationError
from src.core.logging_config import get_logger, get_correlation_id
from src.core.metrics import metrics
from src.ml.model import FakeNewsModel, load_model
from src.ml.preprocessing import clean_text
from src.ml.features import detect_fake_news_red_flags
from src.api.schemas import (
    ArticleRequest, PredictionResponse, BatchRequest, BatchResponse,
    BatchResultItem, HealthResponse, StatsResponse,
)
from src.api.middleware import verify_api_key, RequestTracingMiddleware

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Fake News Detector API",
    description="Industry-grade ML-powered fake news detection API",
    version="3.0.0",
)

# CORS — restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Request tracing
app.add_middleware(RequestTracingMiddleware)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Model loading at startup
# ---------------------------------------------------------------------------
_model: FakeNewsModel | None = None


@app.on_event("startup")
async def startup_event():
    global _model
    try:
        _model = load_model()
        logger.info(f"API model loaded: {_model.version}")
    except Exception as e:
        logger.error(f"Failed to load model at startup: {e}")
        _model = None


def get_model() -> FakeNewsModel:
    if _model is None or not _model.is_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return _model


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "name": "Fake News Detector API",
        "version": "3.0.0",
        "status": "operational" if _model and _model.is_loaded else "degraded",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy" if _model and _model.is_loaded else "unhealthy",
        model_loaded=_model is not None and _model.is_loaded,
        model_version=_model.version if _model else "none",
        database_connected=True,
        gemini_available=bool(settings.GEMINI_API_KEY),
        gnews_configured=bool(settings.GNEWS_API_KEY),
        uptime_seconds=metrics.snapshot()["uptime_seconds"],
        timestamp=datetime.now().isoformat(),
    )


@app.get("/metrics")
async def get_metrics(user: str = Depends(verify_api_key)):
    return metrics.snapshot()


@app.post("/api/v1/analyze", response_model=PredictionResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def analyze_article(
    article: ArticleRequest,
    request: Request,
    model: FakeNewsModel = Depends(get_model),
    user: str = Depends(verify_api_key),
):
    """Analyze a single article for fake news."""
    cleaned = clean_text(article.text)
    if len(cleaned.strip()) < 10:
        raise HTTPException(status_code=400, detail="Text too short after preprocessing")

    result = model.analyze(cleaned)
    red_flags = detect_fake_news_red_flags(article.text)

    return PredictionResponse(
        prediction=result["prediction"],
        confidence=result["confidence"],
        real_probability=result["real_probability"],
        fake_probability=result["fake_probability"],
        red_flag_score=red_flags,
        model_version=result["model_version"],
        timestamp=datetime.now().isoformat(),
        request_id=get_correlation_id(),
    )


@app.post("/api/v1/batch", response_model=BatchResponse)
@limiter.limit(settings.BATCH_RATE_LIMIT)
async def analyze_batch(
    request: Request,
    batch: BatchRequest,
    model: FakeNewsModel = Depends(get_model),
    user: str = Depends(verify_api_key),
):
    """Analyze multiple articles in batch."""
    results = []
    succeeded = 0
    failed = 0

    for article in batch.articles:
        try:
            cleaned = clean_text(article.text)
            r = model.analyze(cleaned)
            red_flags = detect_fake_news_red_flags(article.text)
            results.append(BatchResultItem(
                id=article.id, prediction=r["prediction"],
                confidence=r["confidence"], real_probability=r["real_probability"],
                fake_probability=r["fake_probability"], red_flag_score=red_flags,
            ))
            succeeded += 1
        except Exception as e:
            results.append(BatchResultItem(id=article.id, error=str(e)))
            failed += 1
            logger.error(f"Batch item {article.id} failed: {e}")

    return BatchResponse(
        total=len(batch.articles), processed=len(results),
        succeeded=succeeded, failed=failed, results=results,
        timestamp=datetime.now().isoformat(), request_id=get_correlation_id(),
    )


@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats(user: str = Depends(verify_api_key)):
    """Get API usage statistics (real data, not hardcoded zeros)."""
    snap = metrics.snapshot()
    counters = snap.get("counters", {})
    histograms = snap.get("histograms", {})
    total = counters.get("predictions_total", 0)
    errors = counters.get("errors_total", 0)

    return StatsResponse(
        user=user,
        total_predictions=total,
        predictions_by_type={
            "real": counters.get("predictions_real", 0),
            "fake": counters.get("predictions_fake", 0),
        },
        avg_confidence=histograms.get("prediction_confidence", {}).get("avg", 0),
        avg_latency_ms=histograms.get("prediction_latency_ms", {}).get("avg", 0),
        error_rate=round(errors / max(total, 1), 4),
        uptime_seconds=snap["uptime_seconds"],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
