"""Tests for src.ml.preprocessing — canonical clean_text()."""

import pytest
from src.ml.preprocessing import clean_text, extract_keywords


class TestCleanText:
    def test_basic_cleaning(self):
        result = clean_text("This is a SIMPLE test of the cleaning function.")
        assert isinstance(result, str)
        assert result == result.lower()  # Should be lowercase

    def test_removes_urls(self):
        result = clean_text("Visit https://example.com for more info about this topic today.")
        assert "example.com" not in result
        assert "https" not in result

    def test_removes_html(self):
        result = clean_text("Hello <b>world</b> this is <a href='#'>html</a> content now.")
        assert "<b>" not in result
        assert "<a" not in result

    def test_removes_emails(self):
        result = clean_text("Contact admin@example.com for important details about the project.")
        assert "admin@example.com" not in result

    def test_empty_string(self):
        result = clean_text("")
        assert result == ""

    def test_non_string_input(self):
        result = clean_text(12345)
        assert isinstance(result, str)

    def test_unicode_handling(self):
        result = clean_text("Café résumé naïve über")
        assert isinstance(result, str)

    def test_preserves_meaningful_words(self):
        text = "Scientists discovered new evidence about climate change effects worldwide"
        result = clean_text(text)
        assert len(result) > 0
        # Should have some meaningful words remaining
        assert len(result.split()) >= 2

    def test_very_long_text(self):
        long = "word " * 10000
        result = clean_text(long)
        assert isinstance(result, str)

    def test_stopwords_removed(self):
        result = clean_text("the cat sat on the mat with the hat")
        assert "the" not in result.split()


class TestExtractKeywords:
    def test_basic_extraction(self):
        result = extract_keywords("President Biden met with Congress leaders today")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_respects_max_keywords(self):
        result = extract_keywords("Apple Google Microsoft Amazon Tesla Meta", max_keywords=3)
        assert len(result.split()) <= 3

    def test_empty_input(self):
        result = extract_keywords("")
        assert isinstance(result, str)

    def test_no_capitalized_words(self):
        result = extract_keywords("this is all lowercase text with no proper nouns here")
        assert isinstance(result, str)
