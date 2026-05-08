"""
Application metrics collection.

Provides lightweight, in-process counters and histograms that can be
exported to Prometheus, logged periodically, or queried via /metrics.
"""

import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class _HistogramBucket:
    count: int = 0
    total: float = 0.0
    min_val: float = float("inf")
    max_val: float = float("-inf")
    values: List[float] = field(default_factory=list)

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)
        # Keep last 1000 values for percentile calculation
        if len(self.values) >= 1000:
            self.values.pop(0)
        self.values.append(value)

    @property
    def avg(self) -> float:
        return self.total / self.count if self.count else 0.0

    def percentile(self, p: float) -> float:
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        idx = int(len(sorted_vals) * p / 100)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "avg": round(self.avg, 2),
            "min": round(self.min_val, 2) if self.count else 0,
            "max": round(self.max_val, 2) if self.count else 0,
            "p50": round(self.percentile(50), 2),
            "p95": round(self.percentile(95), 2),
            "p99": round(self.percentile(99), 2),
        }


class MetricsCollector:
    """Thread-safe metrics collector for application telemetry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._histograms: Dict[str, _HistogramBucket] = defaultdict(_HistogramBucket)
        self._gauges: Dict[str, float] = {}
        self._start_time = time.time()

    # --- Counters ---
    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def get_counter(self, name: str) -> int:
        with self._lock:
            return self._counters.get(name, 0)

    # --- Histograms ---
    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._histograms[name].observe(value)

    @contextmanager
    def timer(self, name: str):
        """Context manager to time an operation and record it as a histogram."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.observe(name, elapsed_ms)

    # --- Gauges ---
    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    # --- Export ---
    def snapshot(self) -> dict:
        """Return a JSON-serializable snapshot of all metrics."""
        with self._lock:
            return {
                "uptime_seconds": round(time.time() - self._start_time, 1),
                "counters": dict(self._counters),
                "histograms": {k: v.to_dict() for k, v in self._histograms.items()},
                "gauges": dict(self._gauges),
            }

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()


# Global singleton
metrics = MetricsCollector()


# --- Convenience helpers ---

def record_prediction(prediction: str, confidence: float, latency_ms: float) -> None:
    """Record a single prediction event."""
    metrics.increment("predictions_total")
    metrics.increment(f"predictions_{prediction.lower()}")
    metrics.observe("prediction_confidence", confidence)
    metrics.observe("prediction_latency_ms", latency_ms)


def record_api_call(api_name: str, success: bool, latency_ms: float) -> None:
    """Record an external API call."""
    status = "success" if success else "failure"
    metrics.increment(f"api_{api_name}_{status}")
    metrics.observe(f"api_{api_name}_latency_ms", latency_ms)


def record_error(error_type: str) -> None:
    """Record an error occurrence."""
    metrics.increment("errors_total")
    metrics.increment(f"errors_{error_type}")
