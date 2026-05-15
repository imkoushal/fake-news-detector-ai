"""
Out-of-Distribution (OOD) Detector — Phase 5.1

Detects when an input article is significantly different from the training
data, so the inference pipeline can reduce ML confidence and lean more on
Gemini AI / Web verification.

Approach:
  1. TF-IDF Centroid Distance — compares the input's TF-IDF vector against
     the mean vector of the training set.  Articles far from the centroid
     are likely out-of-distribution.
  2. Vocabulary Overlap — fraction of input tokens present in the TF-IDF
     vocabulary.  Very low overlap means the model has never seen these words.
  3. Structural Heuristics — extremely short text, non-Latin scripts, or
     very high OOV ratio are strong OOD indicators.

The final OOD score is a [0, 1] float:
  0.0 = fully in-distribution (model confident)
  1.0 = completely out-of-distribution (model unreliable)
"""

import numpy as np
import re
from typing import Optional, Tuple


class OODDetector:
    """Detects out-of-distribution inputs relative to training data."""

    def __init__(self, tfidf_vectorizer, centroid: Optional[np.ndarray] = None):
        """
        Args:
            tfidf_vectorizer: Fitted TfidfVectorizer used during training.
            centroid: Precomputed mean TF-IDF vector of the training set.
                      If None, will be computed lazily from training data.
        """
        self.vectorizer = tfidf_vectorizer
        self.vocab = set(tfidf_vectorizer.vocabulary_.keys())
        self.vocab_size = len(self.vocab)
        self._centroid = centroid

        # Precompute IDF statistics for distance normalization
        idf_values = tfidf_vectorizer.idf_
        self._idf_mean = float(np.mean(idf_values))
        self._idf_std = float(np.std(idf_values))

    @classmethod
    def from_training_data(cls, tfidf_vectorizer, X_train_tfidf):
        """Create OOD detector from training data TF-IDF matrix.
        
        Args:
            tfidf_vectorizer: Fitted TfidfVectorizer.
            X_train_tfidf: Sparse TF-IDF matrix of training data.
        """
        # Compute centroid (mean of all training vectors)
        centroid = np.asarray(X_train_tfidf.mean(axis=0)).flatten()
        return cls(tfidf_vectorizer, centroid)

    def _vocabulary_overlap(self, text: str) -> float:
        """Fraction of input tokens that exist in the TF-IDF vocabulary."""
        # Tokenize using the same pattern as TfidfVectorizer
        tokens = re.findall(r'(?u)\b\w\w+\b', text.lower())
        if not tokens:
            return 0.0
        known = sum(1 for t in tokens if t in self.vocab)
        return known / len(tokens)

    def _cosine_distance(self, text: str) -> float:
        """Cosine distance from input to training centroid."""
        if self._centroid is None:
            return 0.5  # Unknown → neutral

        vec = self.vectorizer.transform([text])
        vec_dense = np.asarray(vec.todense()).flatten()

        # Cosine similarity
        dot = np.dot(vec_dense, self._centroid)
        norm_a = np.linalg.norm(vec_dense)
        norm_b = np.linalg.norm(self._centroid)

        if norm_a == 0 or norm_b == 0:
            return 1.0  # Zero vector → completely OOD

        similarity = dot / (norm_a * norm_b)
        # Cosine distance ∈ [0, 2]; map to [0, 1]
        return float(np.clip(1.0 - similarity, 0, 1))

    def _structural_score(self, text: str) -> float:
        """Structural heuristics for OOD detection."""
        score = 0.0

        # Very short text (model trained on articles, not tweets)
        word_count = len(text.split())
        if word_count < 10:
            score += 0.6
        elif word_count < 30:
            score += 0.3
        elif word_count < 50:
            score += 0.1

        # Non-Latin script detection (model only trained on English)
        latin_chars = len(re.findall(r'[a-zA-Z]', text))
        total_alpha = len(re.findall(r'[^\W\d_]', text))  # All unicode letters
        if total_alpha > 0:
            latin_ratio = latin_chars / total_alpha
            if latin_ratio < 0.5:
                score += 0.5  # Predominantly non-Latin → heavy OOD
            elif latin_ratio < 0.8:
                score += 0.2

        # Mostly numbers/symbols (not natural text)
        if len(text) > 0:
            alpha_ratio = total_alpha / len(text.replace(' ', '') or '1')
            if alpha_ratio < 0.3:
                score += 0.3

        return min(score, 1.0)

    def score(self, text: str) -> Tuple[float, dict]:
        """
        Compute OOD score for a single text.

        Returns:
            Tuple of (ood_score, details_dict)
            ood_score: float ∈ [0, 1], higher = more out-of-distribution
            details_dict: breakdown of component scores
        """
        vocab_overlap = self._vocabulary_overlap(text)
        cosine_dist = self._cosine_distance(text)
        structural = self._structural_score(text)

        # Vocab OOD contribution: low overlap → high OOD
        vocab_ood = 1.0 - vocab_overlap

        # Weighted combination
        # Cosine distance is the strongest signal (0.4)
        # Vocabulary overlap is second (0.35)
        # Structural heuristics catch edge cases (0.25)
        ood_score = (
            cosine_dist * 0.40 +
            vocab_ood * 0.35 +
            structural * 0.25
        )

        # Clamp to [0, 1]
        ood_score = float(np.clip(ood_score, 0, 1))

        details = {
            "ood_score": ood_score,
            "cosine_distance": round(cosine_dist, 4),
            "vocabulary_overlap": round(vocab_overlap, 4),
            "structural_score": round(structural, 4),
            "word_count": len(text.split()),
            "is_ood": ood_score > 0.5,
            "confidence_modifier": _ood_to_confidence_modifier(ood_score),
        }

        return ood_score, details

    def score_batch(self, texts):
        """Score multiple texts. Returns list of (score, details) tuples."""
        return [self.score(t) for t in texts]


def _ood_to_confidence_modifier(ood_score: float) -> float:
    """
    Convert OOD score to a confidence modifier for the ML prediction.

    Returns a multiplier ∈ [0.3, 1.0]:
      - ood_score ≈ 0 → modifier ≈ 1.0 (full trust in ML)
      - ood_score ≈ 1 → modifier ≈ 0.3 (minimal trust in ML)
    """
    # Smooth sigmoid-like mapping
    modifier = 1.0 - 0.7 * (ood_score ** 1.5)
    return float(np.clip(modifier, 0.3, 1.0))


def get_dynamic_weights(ood_score: float, gemini_available: bool = True,
                        web_results_count: int = 0) -> dict:
    """
    Phase 5.2: Compute dynamic hybrid weights based on OOD score.

    Default weights: ML=50%, Gemini=30%, Web=20%
    When OOD is high, shift weight away from ML toward Gemini/Web.

    Returns:
        dict with keys: ml_weight, gemini_weight, web_weight (sum to 1.0)
    """
    # Base weights
    ml_w = 0.50
    gemini_w = 0.30
    web_w = 0.20

    if ood_score > 0.3:
        # Reduce ML weight, boost Gemini and Web
        ml_reduction = min(ood_score * 0.4, 0.30)  # Max 30% reduction
        ml_w -= ml_reduction

        if gemini_available:
            gemini_w += ml_reduction * 0.6  # 60% of reduction goes to Gemini
            web_w += ml_reduction * 0.4     # 40% goes to Web
        else:
            web_w += ml_reduction  # All goes to Web if no Gemini

    # Boost web weight if we have many corroborating articles
    if web_results_count >= 5:
        web_boost = 0.05
        ml_w -= web_boost / 2
        gemini_w -= web_boost / 2
        web_w += web_boost

    # Normalize to sum to 1.0
    total = ml_w + gemini_w + web_w
    ml_w /= total
    gemini_w /= total
    web_w /= total

    return {
        "ml_weight": round(ml_w, 4),
        "gemini_weight": round(gemini_w, 4),
        "web_weight": round(web_w, 4),
        "ood_score": round(ood_score, 4),
        "dynamic": ood_score > 0.3,
    }


def calibrate_confidence(raw_confidence: float, ood_score: float) -> float:
    """
    Phase 5.3: Calibrate confidence output.

    Adjusts raw model confidence by the OOD score, producing a more
    honest confidence estimate.  When the model encounters unfamiliar
    text, reported confidence is reduced.

    Args:
        raw_confidence: Model's raw confidence (0-100 scale).
        ood_score: OOD score (0-1 scale).

    Returns:
        Calibrated confidence (0-100 scale).
    """
    modifier = _ood_to_confidence_modifier(ood_score)
    calibrated = raw_confidence * modifier

    # Never report > 95% confidence (epistemic humility)
    calibrated = min(calibrated, 95.0)

    # Floor at 50% for in-distribution, 30% for OOD
    if ood_score > 0.5:
        calibrated = max(calibrated, 30.0)
    else:
        calibrated = max(calibrated, 50.0)

    return round(calibrated, 1)
