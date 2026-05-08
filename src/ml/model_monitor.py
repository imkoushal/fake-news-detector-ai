"""
Model performance monitoring — tracks drift and degradation over time.
"""

import time
from collections import deque
from typing import Dict, Optional

from src.core.logging_config import get_logger
from src.core.metrics import metrics

logger = get_logger(__name__)


class ModelMonitor:
    """Tracks prediction patterns to detect model drift and degradation."""

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self._predictions = deque(maxlen=window_size)
        self._confidences = deque(maxlen=window_size)
        self._disagreements = deque(maxlen=window_size)

    def record(self, prediction: str, confidence: float, ml_agrees_with_gemini: Optional[bool] = None):
        """Record a prediction for monitoring."""
        self._predictions.append(prediction)
        self._confidences.append(confidence)
        if ml_agrees_with_gemini is not None:
            self._disagreements.append(not ml_agrees_with_gemini)
        self._check_alerts()

    def _check_alerts(self):
        """Check for concerning patterns."""
        if len(self._predictions) < 50:
            return
        # Alert if fake ratio spikes
        fake_ratio = sum(1 for p in self._predictions if p == "FAKE") / len(self._predictions)
        metrics.set_gauge("model_fake_ratio", fake_ratio)
        if fake_ratio > 0.8:
            logger.warning(f"High fake ratio detected: {fake_ratio:.0%} of recent predictions are FAKE")
        if fake_ratio < 0.1:
            logger.warning(f"Low fake ratio detected: {fake_ratio:.0%} — model may be under-detecting")
        # Alert if avg confidence drops
        avg_conf = sum(self._confidences) / len(self._confidences) if self._confidences else 0
        metrics.set_gauge("model_avg_confidence", avg_conf)
        if avg_conf < 60:
            logger.warning(f"Low average confidence: {avg_conf:.1f}% — model may be degrading")
        # Alert if ML and Gemini frequently disagree
        if len(self._disagreements) >= 20:
            disagree_rate = sum(self._disagreements) / len(self._disagreements)
            metrics.set_gauge("model_disagreement_rate", disagree_rate)
            if disagree_rate > 0.5:
                logger.warning(f"High ML/Gemini disagreement: {disagree_rate:.0%}")

    def get_stats(self) -> Dict:
        """Return current monitoring statistics."""
        n = len(self._predictions)
        if n == 0:
            return {"total_predictions": 0}
        fake_count = sum(1 for p in self._predictions if p == "FAKE")
        return {
            "total_predictions": n,
            "fake_ratio": round(fake_count / n, 3),
            "real_ratio": round((n - fake_count) / n, 3),
            "avg_confidence": round(sum(self._confidences) / len(self._confidences), 1) if self._confidences else 0,
            "disagreement_rate": round(sum(self._disagreements) / len(self._disagreements), 3) if self._disagreements else None,
        }


# Global singleton
model_monitor = ModelMonitor()
