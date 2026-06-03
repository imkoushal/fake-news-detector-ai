"""
Model Quality Test Suite — Updated for current architecture.

Automated regression tests to ensure model quality is maintained
across training runs.  These tests load the production model and
verify it meets minimum quality bars on both in-distribution
samples and known edge cases.

Run with: pytest tests/test_model_quality.py -v
"""

import sys
from pathlib import Path

import pytest
import numpy as np

from typing import Any, Dict

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── Fixtures ───

@pytest.fixture(scope="module")
def pipeline() -> Any:
    """Load the production model pipeline (once per module).

    Uses FinalModel from app.py which wraps vectorizer + scaler + model
    with combined TF-IDF and meta-feature inference.
    Convention: classes_ = [FAKE=0, REAL=1]
    """
    from joblib import load

    models_dir = PROJECT_ROOT / "models"
    if not (models_dir / "model.joblib").exists():
        pytest.skip("No production model found — run train.py first")

    from app import FinalModel
    vectorizer = load(models_dir / "tfidf.joblib")
    model = load(models_dir / "model.joblib")
    scaler = None
    if (models_dir / "scaler.joblib").exists():
        scaler = load(models_dir / "scaler.joblib")

    ood_detector = None
    if (models_dir / "ood_centroid.npy").exists():
        try:
            from ood_detector import OODDetector
            centroid = np.load(models_dir / "ood_centroid.npy")
            ood_detector = OODDetector(vectorizer, centroid)
        except ImportError:
            pass

    return FinalModel(vectorizer=vectorizer, model=model, scaler=scaler, ood_detector=ood_detector)


@pytest.fixture(scope="module")
def config() -> Dict[str, Any]:
    """Load model config."""
    import json
    config_path = PROJECT_ROOT / "models" / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return json.load(f)


# ─── Known Samples ───

REAL_ARTICLES = [
    # Reuters-style news
    (
        "Washington (Reuters) - The Federal Reserve held interest rates steady on "
        "Wednesday and said it would be patient before adjusting them again as it "
        "seeks to make sure the recent slowdown in inflation is temporary. Fed "
        "Chairman Jerome Powell emphasized patience at a news conference after the "
        "meeting. The decision was unanimous. Markets had been focused on what "
        "signals the central bank would give about its next move."
    ),
    # Business/finance news
    (
        "NEW YORK (Reuters) - U.S. stocks ended higher on Thursday as investors "
        "digested a batch of corporate earnings reports and economic data that "
        "suggested the economy remains resilient. The S&P 500 gained 0.8 percent "
        "to close at a record high, while the Dow Jones Industrial Average rose "
        "0.5 percent. Technology shares led the advance, with Apple Inc rising "
        "2.3 percent after reporting better-than-expected quarterly revenue."
    ),
]

FAKE_ARTICLES = [
    # Classic clickbait conspiracy
    (
        "DOCTORS DON'T WANT YOU TO KNOW: Ancient Himalayan Herb Cures Diabetes in "
        "3 Days! Big Pharma is trying to CENSOR this article! Share before it's "
        "deleted! A revolutionary discovery has sent shockwaves through the medical "
        "establishment. Mainstream media won't report this because pharmaceutical "
        "companies stand to lose BILLIONS! One weird trick that doctors HATE!"
    ),
    # Political misinformation
    (
        "BREAKING!!! SECRET leaked documents prove the DEEP STATE has been "
        "controlling the government for DECADES! The shadowy New World Order "
        "elites are TERRIFIED that you'll see this. Share NOW before they "
        "take this down! The mainstream media is LYING to you! Wake up "
        "sheeple! They don't want you to know the truth!!"
    ),
]


# ─── Model Quality Tests ───

class TestModelLoads:
    """Verify model loads and produces valid outputs."""

    def test_model_exists(self, pipeline):
        assert pipeline is not None

    def test_predict_returns_labels(self, pipeline):
        preds = pipeline.predict(["test article text here"])
        assert preds[0] in [0, 1]

    def test_predict_proba_returns_probabilities(self, pipeline):
        proba = pipeline.predict_proba(["test article text here"])[0]
        assert len(proba) == 2
        assert abs(sum(proba) - 1.0) < 0.01
        assert all(0 <= p <= 1 for p in proba)


class TestMinimumQuality:
    """Verify model meets minimum quality thresholds."""

    def test_accuracy_threshold(self, config):
        """Model accuracy must be >= 90%."""
        if "accuracy" not in config:
            pytest.skip("No accuracy in config")
        assert config["accuracy"] >= 0.90, f"Accuracy {config['accuracy']:.4f} below 90% threshold"

    def test_f1_threshold(self, config):
        """F1 score must be >= 88%."""
        if "f1_score" not in config:
            pytest.skip("No f1_score in config")
        assert config["f1_score"] >= 0.88, f"F1 {config['f1_score']:.4f} below 88% threshold"

    def test_roc_auc_threshold(self, config):
        """ROC-AUC must be >= 95%."""
        if "roc_auc" not in config:
            pytest.skip("No roc_auc in config")
        assert config["roc_auc"] >= 0.95, f"AUC {config['roc_auc']:.4f} below 95% threshold"


class TestRealArticleDetection:
    """Known real articles should be classified as REAL.
    Convention: classes_ = [FAKE=0, REAL=1] → proba[1] = real_prob
    """

    @pytest.mark.parametrize("article", REAL_ARTICLES, ids=["reuters_fed", "reuters_stocks"])
    def test_real_article_prediction(self, pipeline, article):
        from utils import clean_text
        cleaned = clean_text(article)
        proba = pipeline.predict_proba([cleaned], raw_texts=[article])[0]
        # classes_ = [FAKE=0, REAL=1]
        real_prob = float(proba[1])
        assert real_prob > 0.5, (
            f"Real article misclassified: real_prob={real_prob:.3f}"
        )

    @pytest.mark.parametrize("article", REAL_ARTICLES, ids=["reuters_fed", "reuters_stocks"])
    def test_real_article_confidence(self, pipeline, article):
        """Real articles should have > 60% confidence."""
        from utils import clean_text
        cleaned = clean_text(article)
        proba = pipeline.predict_proba([cleaned], raw_texts=[article])[0]
        confidence = max(float(proba[0]), float(proba[1]))
        assert confidence > 0.6, f"Low confidence on real article: {confidence:.3f}"


class TestFakeArticleDetection:
    """Known fake articles should be classified as FAKE.
    Convention: classes_ = [FAKE=0, REAL=1] → proba[0] = fake_prob
    """

    @pytest.mark.parametrize("article", FAKE_ARTICLES, ids=["clickbait_medical", "conspiracy_deepstate"])
    def test_fake_article_prediction(self, pipeline, article):
        from utils import clean_text
        cleaned = clean_text(article)
        proba = pipeline.predict_proba([cleaned], raw_texts=[article])[0]
        # classes_ = [FAKE=0, REAL=1] → fake_prob = proba[0]
        fake_prob = float(proba[0])
        assert fake_prob > 0.5, (
            f"Fake article misclassified: fake_prob={fake_prob:.3f}"
        )

    @pytest.mark.parametrize("article", FAKE_ARTICLES, ids=["clickbait_medical", "conspiracy_deepstate"])
    def test_fake_article_confidence(self, pipeline, article):
        """Fake articles should have > 60% confidence."""
        from utils import clean_text
        cleaned = clean_text(article)
        proba = pipeline.predict_proba([cleaned], raw_texts=[article])[0]
        confidence = max(float(proba[0]), float(proba[1]))
        assert confidence > 0.6, f"Low confidence on fake article: {confidence:.3f}"


class TestOODDetection:
    """OOD detector should flag unusual inputs."""

    def test_ood_on_normal_article(self, pipeline):
        """Normal English news article should NOT be OOD."""
        if pipeline.ood is None:
            pytest.skip("OOD centroid not yet computed (run train.py first)")
        article = REAL_ARTICLES[0]
        score, details = pipeline.ood_score(article)
        assert score < 0.6, f"Normal article flagged as OOD: {score:.3f}"

    def test_ood_on_very_short_text(self, pipeline):
        """Very short text should have elevated OOD score."""
        if pipeline.ood is None:
            pytest.skip("OOD centroid not yet computed (run train.py first)")
        score, details = pipeline.ood_score("Hello world")
        assert score > 0.3, f"Short text not detected as OOD: {score:.3f}"

    def test_ood_on_non_english(self, pipeline):
        """Non-English text should be strongly OOD."""
        if pipeline.ood is None:
            pytest.skip("OOD centroid not yet computed (run train.py first)")
        score, details = pipeline.ood_score("これは日本語のテストテキストです。フェイクニュースの検出テスト。")
        assert score > 0.4, f"Non-English text not detected as OOD: {score:.3f}"

    def test_ood_returns_details(self, pipeline):
        """OOD detector should return useful detail keys."""
        if pipeline.ood is None:
            pytest.skip("OOD centroid not yet computed (run train.py first)")
        _, details = pipeline.ood_score("Test article text")
        assert "ood_score" in details
        assert "is_ood" in details
        assert "confidence_modifier" in details

    def test_ood_score_range(self, pipeline):
        """OOD score should be between 0 and 1."""
        if pipeline.ood is None:
            pytest.skip("OOD centroid not yet computed (run train.py first)")
        for article in REAL_ARTICLES + FAKE_ARTICLES:
            score, _ = pipeline.ood_score(article)
            assert 0.0 <= score <= 1.0, f"OOD score out of range: {score}"


class TestDynamicWeights:
    """Dynamic weight computation."""

    def test_normal_weights(self):
        from ood_detector import get_dynamic_weights
        weights = get_dynamic_weights(0.0)
        assert abs(weights["ml_weight"] - 0.5) < 0.05
        assert abs(weights["gemini_weight"] - 0.3) < 0.05
        assert abs(weights["web_weight"] - 0.2) < 0.05

    def test_ood_reduces_ml_weight(self):
        from ood_detector import get_dynamic_weights
        weights = get_dynamic_weights(0.8)
        assert weights["ml_weight"] < 0.4, "High OOD should reduce ML weight"
        assert weights["gemini_weight"] > 0.3, "High OOD should increase Gemini weight"

    def test_weights_sum_to_one(self):
        from ood_detector import get_dynamic_weights
        for ood in [0.0, 0.3, 0.5, 0.7, 1.0]:
            weights = get_dynamic_weights(ood)
            total = weights["ml_weight"] + weights["gemini_weight"] + weights["web_weight"]
            assert abs(total - 1.0) < 0.01, f"Weights don't sum to 1: {total}"


class TestConfidenceCalibration:
    """Confidence calibration."""

    def test_in_distribution_confidence(self):
        from ood_detector import calibrate_confidence
        cal = calibrate_confidence(90.0, 0.0)
        assert cal >= 80.0, "In-distribution confidence should remain high"

    def test_ood_reduces_confidence(self):
        from ood_detector import calibrate_confidence
        cal_normal = calibrate_confidence(90.0, 0.0)
        cal_ood = calibrate_confidence(90.0, 0.8)
        assert cal_ood < cal_normal, "OOD should reduce confidence"

    def test_max_confidence_cap(self):
        from ood_detector import calibrate_confidence
        cal = calibrate_confidence(99.0, 0.0)
        assert cal <= 95.0, "Confidence should never exceed 95%"

    def test_min_confidence_floor(self):
        from ood_detector import calibrate_confidence
        cal = calibrate_confidence(20.0, 0.0)
        assert cal >= 30.0, "In-distribution confidence floor is 30%"


class TestEdgeCases:
    """Edge cases that should not crash."""

    def test_empty_text(self, pipeline):
        """Empty text should not crash."""
        from utils import clean_text
        cleaned = clean_text("")
        if cleaned.strip():
            proba = pipeline.predict_proba([cleaned])[0]
            assert len(proba) == 2

    def test_very_long_text(self, pipeline):
        """Very long text should not crash."""
        from utils import clean_text
        long_text = "This is a test sentence. " * 1000
        cleaned = clean_text(long_text)
        proba = pipeline.predict_proba([cleaned], raw_texts=[long_text])[0]
        assert len(proba) == 2

    def test_special_characters(self, pipeline):
        """Special characters should not crash."""
        from utils import clean_text
        text = "!!!@@@###$$$%%%^^^&&&***((())) testing special chars article"
        cleaned = clean_text(text)
        if cleaned.strip():
            proba = pipeline.predict_proba([cleaned])[0]
            assert len(proba) == 2

    def test_numeric_only(self, pipeline):
        """Numeric-only text should not crash."""
        from utils import clean_text
        cleaned = clean_text("123456789 0.5 3.14 100%")
        if cleaned.strip():
            proba = pipeline.predict_proba([cleaned])[0]
            assert len(proba) == 2

    def test_unicode_text(self, pipeline):
        """Unicode text should not crash the pipeline."""
        from utils import clean_text
        text = "El presidente anunció nuevas medidas económicas según fuentes oficiales del gobierno"
        cleaned = clean_text(text)
        if cleaned.strip():
            proba = pipeline.predict_proba([cleaned])[0]
            assert len(proba) == 2

    def test_mixed_language_text(self, pipeline):
        """Mixed language text should not crash."""
        from utils import clean_text
        text = "Breaking news from Tokyo 東京 — officials say the earthquake measured 5.2 on the Richter scale"
        cleaned = clean_text(text)
        if cleaned.strip():
            proba = pipeline.predict_proba([cleaned])[0]
            assert len(proba) == 2
