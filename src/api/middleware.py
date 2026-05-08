"""
FastAPI middleware — authentication, CORS, error handling, request tracing.
"""

import hashlib
import time

from fastapi import Header, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings
from src.core.logging_config import get_logger, set_correlation_id
from src.core.metrics import metrics

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# API key authentication
# ---------------------------------------------------------------------------
def verify_api_key(x_api_key: str = Header(None)) -> str:
    """Verify API key from request header. Returns the associated username."""
    if not settings.API_KEYS:
        # No keys configured — allow unauthenticated access in dev mode
        if settings.is_development:
            return "anonymous_dev"
        raise HTTPException(status_code=401, detail="API keys not configured")

    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    user = settings.API_KEYS.get(x_api_key)
    if not user:
        logger.warning("Invalid API key attempt", extra={"endpoint": "auth"})
        raise HTTPException(status_code=401, detail="Invalid API key")

    return user


# ---------------------------------------------------------------------------
# Request tracing middleware
# ---------------------------------------------------------------------------
class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Adds correlation ID and timing to every request."""

    async def dispatch(self, request: Request, call_next):
        cid = set_correlation_id()
        request.state.correlation_id = cid
        start = time.perf_counter()

        response = await call_next(request)

        latency_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Correlation-ID"] = cid
        response.headers["X-Response-Time-Ms"] = str(round(latency_ms, 1))

        metrics.observe("http_request_latency_ms", latency_ms)
        metrics.increment(f"http_{response.status_code}")

        logger.info(
            f"{request.method} {request.url.path} → {response.status_code}",
            extra={
                "endpoint": request.url.path,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 1),
                "request_id": cid,
            },
        )
        return response
