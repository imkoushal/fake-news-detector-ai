"""Tests for backend/card_generator.py — SVG verdict card generation."""
import pytest
from backend.card_generator import generate_verdict_card


class TestGenerateVerdictCard:
    def test_generates_valid_svg(self):
        svg = generate_verdict_card(
            claim_text="Test claim about something",
            verdict="LIKELY_FALSE",
            confidence=85.5,
            analysis="This claim appears to be false based on evidence.",
        )
        assert svg.startswith("<svg")
        assert "1200" in svg  # width
        assert "630" in svg   # height
        assert "</svg>" in svg

    def test_likely_true_card(self):
        svg = generate_verdict_card(
            claim_text="A true claim",
            verdict="LIKELY_TRUE",
            confidence=92,
            analysis="Supported by multiple sources.",
        )
        assert "LIKELY TRUE" in svg
        assert "#4ADE80" in svg  # green color
        assert "92" in svg

    def test_likely_false_card(self):
        svg = generate_verdict_card(
            claim_text="A false claim",
            verdict="LIKELY_FALSE",
            confidence=78,
            analysis="No sources support this.",
        )
        assert "LIKELY FALSE" in svg
        assert "#EF4444" in svg  # red color

    def test_mixed_verdict(self):
        svg = generate_verdict_card(
            claim_text="A mixed claim",
            verdict="MIXED",
            confidence=55,
        )
        assert "MIXED" in svg
        assert "#F59E0B" in svg  # amber color

    def test_long_text_truncated(self):
        long_text = "A" * 500
        svg = generate_verdict_card(
            claim_text=long_text,
            verdict="LIKELY_TRUE",
            confidence=80,
        )
        # Should not contain the full 500 chars
        assert "A" * 200 not in svg

    def test_html_entities_escaped(self):
        svg = generate_verdict_card(
            claim_text='Test <script>alert("xss")</script>',
            verdict="LIKELY_FALSE",
            confidence=90,
            analysis='Contains "quotes" & <tags>',
        )
        assert "<script>" not in svg
        assert "&lt;script&gt;" in svg
