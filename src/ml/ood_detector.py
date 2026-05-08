"""
Out-of-Distribution (OOD) detection for the Fake News Detector.

Detects when input text is too different from the training distribution
and returns "uncertain / out of scope" instead of a confident wrong prediction.
"""

import numpy as np
from typing import Dict, Optional

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class OODDetector:
    """
    Lightweight OOD detector using TF-IDF feature statistics.
    
    Approach: if the input text produces a very sparse TF-IDF vector
    (few known vocabulary tokens), the model can't make an informed prediction.
    We also check prediction entropy to flag uncertain outputs.
    """

    def __init__(self, min_known_token_ratio: float = 0.1, entropy_threshold: float = 0.9):
        self.min_known_token_ratio = min_known_token_ratio
        self.entropy_threshold = entropy_threshold
        self._vocab_size: Optional[int] = None

    def configure(self, vectorizer) -> None:
        """Configure the detector with the fitted vectorizer's vocabulary."""
        if hasattr(vectorizer, "vocabulary_"):
            self._vocab_size = len(vectorizer.vocabulary_)
            logger.info(f"OOD detector configured with vocabulary size: {self._vocab_size}")

    def check(self, text: str, cleaned_text: str, vectorizer, probabilities: np.ndarray) -> Dict:
        """
        Check if the input is out-of-distribution.

        Returns a dict with:
          - is_ood: bool — True if the input is likely OOD
          - confidence_adjustment: float — multiplier for model confidence (0-1)
          - reasons: list[str] — human-readable explanations
        """
        reasons = []
        confidence_adj = 1.0

        # Check 1: Vocabulary overlap
        if hasattr(vectorizer, "vocabulary_"):
            text_tokens = set(cleaned_text.lower().split())
            vocab_tokens = set(vectorizer.vocabulary_.keys())
            if text_tokens:
                overlap = len(text_tokens & vocab_tokens) / len(text_tokens)
                if overlap < self.min_known_token_ratio:
                    reasons.append(
                        f"Low vocabulary overlap ({overlap:.0%}): text contains mostly unknown words"
                    )
                    confidence_adj *= 0.5
                elif overlap < 0.3:
                    reasons.append(
                        f"Moderate vocabulary overlap ({overlap:.0%}): text may be outside training domain"
                    )
                    confidence_adj *= 0.7

        # Check 2: Prediction entropy
        entropy = self._prediction_entropy(probabilities)
        if entropy > self.entropy_threshold:
            reasons.append(
                f"High prediction uncertainty (entropy: {entropy:.2f}): model is not confident"
            )
            confidence_adj *= 0.6

        # Check 3: Text length anomaly
        word_count = len(text.split())
        if word_count < 20:
            reasons.append("Very short text: model was trained on full articles")
            confidence_adj *= 0.7

        is_ood = len(reasons) > 0

        if is_ood:
            logger.warning("OOD input detected", extra={"article_length": len(text)})

        return {
            "is_ood": is_ood,
            "confidence_adjustment": round(confidence_adj, 2),
            "reasons": reasons,
        }

    @staticmethod
    def _prediction_entropy(probabilities: np.ndarray) -> float:
        """Calculate Shannon entropy of prediction probabilities."""
        probs = np.clip(probabilities, 1e-10, 1.0)
        return float(-np.sum(probs * np.log2(probs)))


# Global singleton
ood_detector = OODDetector()
