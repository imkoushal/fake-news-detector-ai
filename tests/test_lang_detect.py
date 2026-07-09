"""Tests for backend/lang_detect.py — Indic language detection."""
import pytest
from backend.lang_detect import detect_language, needs_indic_routing


class TestDetectLanguage:
    def test_english_text(self):
        result = detect_language("Breaking news: The president announced a new policy today.")
        assert result["lang"] == "en"
        assert result["is_indic"] is False

    def test_hindi_devanagari(self):
        result = detect_language("यह एक फर्जी खबर है जो व्हाट्सएप पर वायरल हो रही है")
        assert result["lang"] == "hi"
        assert result["script"] == "devanagari"
        assert result["is_indic"] is True

    def test_hinglish_text(self):
        result = detect_language("yeh khabar jhooth hai bhai, sarkar ne koi yojana nahi nikali hai")
        assert result["lang"] == "hinglish"
        assert result["is_indic"] is True

    def test_bengali_text(self):
        result = detect_language("এটি একটি ভুয়া খবর যা হোয়াটসঅ্যাপে ভাইরাল হচ্ছে")
        assert result["lang"] == "bn"
        assert result["script"] == "bengali"
        assert result["is_indic"] is True

    def test_mixed_hindi_english(self):
        # Text with significant Devanagari should be detected as Hindi
        result = detect_language("PM Modi ने कहा कि भारत में नई योजना शुरू होगी next month")
        assert result["is_indic"] is True

    def test_very_short_text(self):
        result = detect_language("hi")
        assert result["lang"] == "en"
        assert result["is_indic"] is False

    def test_empty_text(self):
        result = detect_language("")
        assert result["lang"] == "en"
        assert result["is_indic"] is False


class TestNeedsIndicRouting:
    def test_english_no_routing(self):
        assert needs_indic_routing("This is a normal English article about politics.") is False

    def test_hindi_needs_routing(self):
        assert needs_indic_routing("यह एक फर्जी खबर है") is True

    def test_hinglish_needs_routing(self):
        assert needs_indic_routing("yeh sach hai bhai kya sarkar ne yojana nikali hai dekho") is True
