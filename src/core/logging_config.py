"""
Structured logging configuration.

Provides JSON-formatted logs in production and human-readable logs in
development.  Every module should obtain a logger via:

    from src.core.logging_config import get_logger
    logger = get_logger(__name__)
"""

import logging
import logging.handlers
import json
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.core.config import settings

# ---------------------------------------------------------------------------
# Correlation / request ID propagation via contextvars
# ---------------------------------------------------------------------------
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set (or generate) a correlation ID for the current async context."""
    cid = cid or uuid.uuid4().hex[:12]
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    return _correlation_id.get("")


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------
class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line — ready for ELK / CloudWatch / Loki."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        cid = get_correlation_id()
        if cid:
            log_entry["correlation_id"] = cid

        # Attach extra fields if provided (e.g. logger.info("msg", extra={...}))
        for key in ("article_length", "prediction", "confidence", "latency_ms",
                     "error_type", "model_version", "endpoint", "status_code",
                     "batch_size", "api_name", "request_id"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }
        return json.dumps(log_entry, default=str)


class HumanReadableFormatter(logging.Formatter):
    """Coloured, human-readable formatter for local development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        cid = get_correlation_id()
        cid_str = f" [{cid}]" if cid else ""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        msg = record.getMessage()
        base = f"{color}{ts} {record.levelname:<8}{self.RESET}{cid_str} {record.name} | {msg}"
        if record.exc_info and record.exc_info[1]:
            base += f"\n  ↳ {type(record.exc_info[1]).__name__}: {record.exc_info[1]}"
        return base


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
_configured = False


def _configure_root_logger() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT == "json":
        console.setFormatter(JSONFormatter())
    else:
        console.setFormatter(HumanReadableFormatter())
    root.addHandler(console)

    # Rotating file handler — always JSON for machine parsing
    log_dir = settings.PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())
    root.addHandler(file_handler)

    # Suppress noisy third-party loggers
    for noisy in ("urllib3", "httpcore", "httpx", "google", "grpc"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger, ensuring the root logger is configured."""
    _configure_root_logger()
    return logging.getLogger(name)
