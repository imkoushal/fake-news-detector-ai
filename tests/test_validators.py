"""Tests for src.core.validators."""

import pytest
import pandas as pd
from src.core.validators import validate_article_text, validate_csv_upload, check_article_quality, validate_url
from src.core.exceptions import ArticleTooShortError, ArticleTooLongError, ValidationError


class TestValidateArticleText:
    def test_valid_text(self):
        text = "A" * 200
        result = validate_article_text(text)
        assert result == text

    def test_strips_whitespace(self):
        text = "  " + "A" * 200 + "  "
        result = validate_article_text(text)
        assert result == "A" * 200

    def test_too_short_raises(self):
        with pytest.raises(ArticleTooShortError):
            validate_article_text("Too short", min_length=100)

    def test_too_long_raises(self):
        with pytest.raises(ArticleTooLongError):
            validate_article_text("A" * 100_000, max_length=50_000)

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            validate_article_text("")

    def test_non_string_raises(self):
        with pytest.raises(ValidationError):
            validate_article_text(12345)

    def test_non_printable_raises(self):
        text = "\x00" * 200
        with pytest.raises(ValidationError, match="non-printable"):
            validate_article_text(text)

    def test_custom_min_length(self):
        result = validate_article_text("Hello world test", min_length=5)
        assert result == "Hello world test"


class TestCheckArticleQuality:
    def test_short_text_warns(self):
        result = check_article_quality("Short text.")
        assert result["quality_warning"] is not None
        assert not result["is_recommended_length"]

    def test_long_text_no_warning(self):
        result = check_article_quality("A " * 500)
        assert result["quality_warning"] is None
        assert result["is_recommended_length"]


class TestValidateCsvUpload:
    def test_valid_csv(self):
        df = pd.DataFrame({"text": ["article 1", "article 2"]})
        result_df, col = validate_csv_upload(df)
        assert col == "text"
        assert len(result_df) == 2

    def test_content_column(self):
        df = pd.DataFrame({"content": ["article 1"]})
        _, col = validate_csv_upload(df)
        assert col == "content"

    def test_no_text_column_raises(self):
        df = pd.DataFrame({"foo": ["bar"]})
        with pytest.raises(ValidationError, match="No suitable text column"):
            validate_csv_upload(df)

    def test_empty_csv_raises(self):
        df = pd.DataFrame()
        with pytest.raises(ValidationError, match="empty"):
            validate_csv_upload(df)

    def test_too_many_rows_raises(self):
        df = pd.DataFrame({"text": ["x"] * 1000})
        with pytest.raises(ValidationError, match="rows"):
            validate_csv_upload(df, max_rows=500)


class TestValidateUrl:
    def test_valid_url(self):
        assert validate_url("https://example.com") == "https://example.com"

    def test_adds_https(self):
        assert validate_url("example.com").startswith("https://")

    def test_invalid_url_raises(self):
        with pytest.raises(ValidationError):
            validate_url("not-a-url")

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_url("")
