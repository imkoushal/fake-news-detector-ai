"""
Centralized configuration management.

Loads settings from environment variables with .env file fallback.
Every configurable value in the application flows through this module.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env file (no-op in production where env vars are injected by platform)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_env_path = _PROJECT_ROOT / ".env"
load_dotenv(_env_path, override=False)


def _parse_api_keys(raw: str) -> Dict[str, str]:
    """Parse 'key1:user1,key2:user2' format into a dict."""
    if not raw:
        return {}
    result = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            key, user = pair.split(":", 1)
            result[key.strip()] = user.strip()
    return result


def _parse_cors_origins(raw: str) -> List[str]:
    """Parse comma-separated CORS origins."""
    if not raw:
        return []
    return [o.strip() for o in raw.split(",") if o.strip()]


@dataclass(frozen=True)
class Settings:
    """Immutable application-wide settings populated from environment."""

    # --- Environment ---
    APP_ENV: str = os.getenv("APP_ENV", "development")
    PROJECT_ROOT: Path = _PROJECT_ROOT

    # --- External API keys ---
    GNEWS_API_KEY: str = os.getenv("GNEWS_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # --- API authentication ---
    API_KEYS: Dict[str, str] = field(
        default_factory=lambda: _parse_api_keys(os.getenv("API_KEYS", ""))
    )

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    # --- Model ---
    MODEL_DIR: Path = field(
        default_factory=lambda: _PROJECT_ROOT / os.getenv("MODEL_DIR", "models")
    )
    MODEL_VERSION: str = os.getenv("MODEL_VERSION", "latest")
    PREDICTION_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("PREDICTION_CONFIDENCE_THRESHOLD", "0.5")
    )

    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{_PROJECT_ROOT / 'analysis_history.db'}"
    )
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))

    # --- Rate limiting ---
    API_RATE_LIMIT: str = os.getenv("API_RATE_LIMIT", "30/minute")
    BATCH_RATE_LIMIT: str = os.getenv("BATCH_RATE_LIMIT", "10/minute")
    MAX_BATCH_SIZE: int = int(os.getenv("MAX_BATCH_SIZE", "50"))

    # --- External API settings ---
    GNEWS_TIMEOUT_SECONDS: int = int(os.getenv("GNEWS_TIMEOUT_SECONDS", "10"))
    GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

    # --- CORS ---
    CORS_ALLOWED_ORIGINS: List[str] = field(
        default_factory=lambda: _parse_cors_origins(
            os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8501")
        )
    )

    # --- Feature flags ---
    ENABLE_GEMINI_VERIFICATION: bool = os.getenv("ENABLE_GEMINI_VERIFICATION", "true").lower() == "true"
    ENABLE_WEB_SEARCH: bool = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
    ENABLE_OOD_DETECTION: bool = os.getenv("ENABLE_OOD_DETECTION", "true").lower() == "true"

    # --- Article limits ---
    MIN_ARTICLE_LENGTH: int = 100
    MAX_ARTICLE_LENGTH: int = 50_000
    RECOMMENDED_ARTICLE_LENGTH: int = 500

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


# Singleton instance — import this everywhere
settings = Settings()
