"""
Unified model wrapper for the Fake News Detector.

Single definition of FakeNewsModel (replaces two divergent FinalModel classes).
"""

import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

from src.core.config import settings
from src.core.exceptions import ModelLoadError, ModelNotLoadedError, PredictionError
from src.core.logging_config import get_logger
from src.core.metrics import record_prediction

logger = get_logger(__name__)


class FakeNewsModel(BaseEstimator, ClassifierMixin):
    """Unified model wrapper with metrics, logging, and version tracking."""

    def __init__(self, vectorizer=None, model=None, config=None, version="unknown"):
        self.vectorizer = vectorizer
        self.model = model
        self.config = config or {}
        self.version = version
        self._is_loaded = vectorizer is not None and model is not None

    @property
    def is_loaded(self):
        return self._is_loaded

    def predict(self, X):
        self._check_loaded()
        try:
            X_tfidf = self.vectorizer.transform(X)
            return self.model.predict(X_tfidf)
        except Exception as e:
            raise PredictionError(f"Prediction failed: {e}") from e

    def predict_proba(self, X):
        self._check_loaded()
        try:
            X_tfidf = self.vectorizer.transform(X)
            return self.model.predict_proba(X_tfidf)
        except Exception as e:
            raise PredictionError(f"Probability prediction failed: {e}") from e

    def analyze(self, cleaned_text: str) -> Dict:
        """Run full prediction on cleaned text with metrics recording."""
        start = time.perf_counter()
        proba = self.predict_proba([cleaned_text])[0]
        real_prob = float(proba[0])
        fake_prob = float(proba[1])
        prediction = "FAKE" if fake_prob > 0.5 else "REAL"
        confidence = max(real_prob, fake_prob) * 100
        latency_ms = (time.perf_counter() - start) * 1000
        record_prediction(prediction, confidence, latency_ms)
        logger.info("Model prediction complete", extra={
            "prediction": prediction, "confidence": round(confidence, 2),
            "latency_ms": round(latency_ms, 2), "model_version": self.version,
        })
        return {
            "prediction": prediction, "confidence": confidence,
            "real_probability": real_prob, "fake_probability": fake_prob,
            "model_version": self.version, "latency_ms": round(latency_ms, 2),
        }

    def _check_loaded(self):
        if not self._is_loaded:
            raise ModelNotLoadedError("Model not loaded. Check model files.")

    def get_individual_predictions(self, text_features) -> Dict:
        """Get predictions from individual estimators in an ensemble."""
        predictions = {}
        model_to_inspect = self.model
        if hasattr(model_to_inspect, "estimator"):
            model_to_inspect = model_to_inspect.estimator
        if hasattr(model_to_inspect, "estimators_"):
            for i, est in enumerate(model_to_inspect.estimators_):
                try:
                    pred = est.predict(text_features)[0]
                    proba = est.predict_proba(text_features)[0] if hasattr(est, "predict_proba") else [0.5, 0.5]
                    predictions[f"Model_{i+1}"] = {"prediction": "FAKE" if pred == 1 else "REAL", "confidence": round(max(proba) * 100, 1)}
                except Exception as e:
                    logger.debug(f"Estimator {i} failed: {e}")
                    predictions[f"Model_{i+1}"] = {"prediction": "N/A", "confidence": 0.0}
        return predictions


def load_model(model_dir: Optional[Path] = None) -> FakeNewsModel:
    """Load model artifacts with clear fallback chain. Raises ModelLoadError on failure."""
    import joblib
    model_dir = model_dir or settings.MODEL_DIR
    config = {}
    config_path = model_dir / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config.json: {e}")

    # Strategy 1: model.joblib + tfidf.joblib
    mp, tp = model_dir / "model.joblib", model_dir / "tfidf.joblib"
    if mp.exists() and tp.exists():
        try:
            vec = joblib.load(tp)
            mdl = joblib.load(mp)
            logger.info("Model loaded (model.joblib + tfidf.joblib)")
            return FakeNewsModel(vectorizer=vec, model=mdl, config=config, version=config.get("model_type", "v1"))
        except Exception as e:
            logger.error(f"Strategy 1 failed: {e}")

    # Strategy 2: pipeline_optimized.joblib
    op = model_dir / "pipeline_optimized.joblib"
    if op.exists():
        try:
            data = joblib.load(op)
            if isinstance(data, dict) and "vectorizer" in data:
                logger.info("Model loaded (pipeline_optimized.joblib dict)")
                return FakeNewsModel(vectorizer=data["vectorizer"], model=data["model"], config=config, version="optimized")
        except Exception as e:
            logger.error(f"Strategy 2 failed: {e}")

    # Strategy 3: pipeline.joblib (skip corrupt 2-byte files)
    pp = model_dir / "pipeline.joblib"
    if pp.exists() and pp.stat().st_size > 10:
        try:
            pipe = joblib.load(pp)
            if hasattr(pipe, "predict_proba"):
                logger.info("Model loaded (pipeline.joblib legacy)")
                return FakeNewsModel(vectorizer=pipe, model=pipe, config=config, version="legacy")
        except Exception as e:
            logger.error(f"Strategy 3 failed: {e}")

    raise ModelLoadError(f"No valid model found in {model_dir}.")
