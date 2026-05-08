"""Tests for src.ml.features."""

import pytest
from src.ml.features import (
    extract_features, get_conspiracy_indicators, get_sensationalism_score,
    classify_topic, highlight_suspicious_phrases, calculate_readability_score,
    detect_fake_news_red_flags, extract_domain, analyze_source, extract_time_references,
)


class TestExtractFeatures:
    def test_basic_features(self):
        result = extract_features("Hello world. How are you? Great!")
        assert result["sentence_count"] == 3
        assert result["question_count"] == 1
        assert result["exclamation_count"] == 1
        assert result["total_words"] > 0

    def test_empty_text(self):
        result = extract_features("")
        assert result["total_words"] == 0


class TestConspiracyIndicators:
    def test_detects_conspiracy(self):
        assert get_conspiracy_indicators("The deep state is real. Illuminati controls everything.") >= 2

    def test_clean_text(self):
        assert get_conspiracy_indicators("The weather is nice today.") == 0


class TestSensationalismScore:
    def test_detects_sensationalism(self):
        score = get_sensationalism_score("SHOCKING! This is INCREDIBLE and UNBELIEVABLE news!")
        assert score > 0

    def test_clean_text(self):
        score = get_sensationalism_score("The quarterly report shows steady growth in the sector.")
        assert score == 0 or score < 0.1

    def test_empty(self):
        assert get_sensationalism_score("") == 0


class TestClassifyTopic:
    def test_politics(self):
        topic, conf = classify_topic("The president signed a new policy after congress voted.")
        assert topic == "politics"
        assert conf > 0

    def test_health(self):
        topic, _ = classify_topic("The doctor prescribed a new treatment for the disease.")
        assert topic == "health"

    def test_unknown(self):
        topic, conf = classify_topic("xyzzy foobar baz")
        assert topic == "general"
        assert conf == 0.0


class TestHighlightSuspicious:
    def test_detects_clickbait(self, sample_fake_article):
        findings = highlight_suspicious_phrases(sample_fake_article)
        assert len(findings) > 0
        categories = {f["category"] for f in findings}
        assert len(categories) >= 1  # Should find at least one type

    def test_clean_article(self, sample_real_article):
        findings = highlight_suspicious_phrases(sample_real_article)
        # Real articles should have few or no suspicious phrases
        high_severity = [f for f in findings if f["severity"] == "high"]
        assert len(high_severity) == 0


class TestReadability:
    def test_basic(self):
        result = calculate_readability_score("The cat sat on the mat. It was a good cat.")
        assert "grade_level" in result
        assert "difficulty" in result
        assert result["word_count"] > 0

    def test_empty(self):
        result = calculate_readability_score("")
        assert result["grade_level"] == 0


class TestRedFlags:
    def test_detects_red_flags(self, sample_fake_article):
        score = detect_fake_news_red_flags(sample_fake_article)
        assert score > 0.3  # Should catch many red flags

    def test_clean_article(self, sample_real_article):
        score = detect_fake_news_red_flags(sample_real_article)
        assert score < 0.3

    def test_score_range(self, sample_fake_article):
        score = detect_fake_news_red_flags(sample_fake_article)
        assert 0.0 <= score <= 1.0


class TestExtractDomain:
    def test_extracts_domain(self):
        assert extract_domain("Visit https://www.reuters.com/article for news.") == "reuters.com"

    def test_no_url(self):
        assert extract_domain("No URLs here.") is None


class TestAnalyzeSource:
    def test_trusted(self):
        result = analyze_source("reuters.com")
        assert result["category"] == "trusted"
        assert result["reputation"] == 95

    def test_unreliable(self):
        result = analyze_source("infowars.com")
        assert result["category"] == "unreliable"

    def test_unknown(self):
        result = analyze_source("unknown-blog.xyz")
        assert result["category"] == "unknown"

    def test_none(self):
        result = analyze_source(None)
        assert result["category"] == "unknown"


class TestTimeReferences:
    def test_detects_relative(self):
        refs = extract_time_references("Yesterday the president spoke. Last week there was a meeting.")
        assert len(refs) >= 1
