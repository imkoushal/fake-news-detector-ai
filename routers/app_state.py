"""
Shared application state for api.py and routers.

All mutable globals (model artifacts, caches, config) live here so that
both the main app module and extracted routers can access them without
circular imports.

Populated at startup by api.py's lifespan handler (via _load_model).
"""
import os
import logging
from pathlib import Path

# ── Base Directory ──
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Version ──
APP_VERSION = "9.0"

# ── Production detection ──
IS_PRODUCTION = (
    os.getenv("APP_ENV", "").lower() in ("production", "prod")
    or bool(os.getenv("RENDER"))
)

# ── Admin secret ──
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")

# ── ML Model state (populated by _load_model in api.py) ──
MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))
MODEL_VERSION = APP_VERSION  # fallback
MODEL_METRICS: dict = {}
MODEL_LOADED = False
MODEL_THRESHOLD = 0.5
model = None
tfidf = None
scaler = None
ood_detector_instance = None

# ── Claim cache (instantiated immediately) ──
from backend.cache import ClaimCache  # noqa: E402
claim_cache = ClaimCache(max_size=500, ttl_seconds=3600)
