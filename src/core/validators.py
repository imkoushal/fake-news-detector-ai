"""
Input validators for the Fake News Detector.

All validation functions raise src.core.exceptions.ValidationError (or a
subclass) on failure and return the cleaned / normalized value on success.
"""

import re
from typing import Optional
from urllib.parse import urlparse

import pandas as pd

from src.core.config import settings
from src.core.exceptions import (
    ArticleTooLongError,
    ArticleTooShortError,
    ValidationError,
)
from src.core.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Article text validation
# ---------------------------------------------------------------------------

def validate_article_text(
    text: str,
    *,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
) -> str:
    """
    Validate and normalize article text.

    Returns the cleaned text on success.
    Raises ArticleTooShortError / ArticleTooLongError / ValidationError on failure.
    """
    min_len = min_length or settings.MIN_ARTICLE_LENGTH
    max_len = max_length or settings.MAX_ARTICLE_LENGTH

    if not isinstance(text, str):
        raise ValidationError("Article text must be a string.")

    # Normalize whitespace but preserve original for analysis
    text = text.strip()

    if not text:
        raise ValidationError("Article text cannot be empty.")

    if len(text) < min_len:
        raise ArticleTooShortError(
            f"Article text too short ({len(text)} chars). Minimum is {min_len} characters.",
            details={"length": len(text), "minimum": min_len},
        )

    if len(text) > max_len:
        raise ArticleTooLongError(
            f"Article text too long ({len(text)} chars). Maximum is {max_len} characters.",
            details={"length": len(text), "maximum": max_len},
        )

    # Check for non-printable / garbage characters
    printable_ratio = sum(1 for c in text if c.isprintable() or c in "\n\r\t") / len(text)
    if printable_ratio < 0.8:
        raise ValidationError(
            "Article text contains too many non-printable characters.",
            details={"printable_ratio": round(printable_ratio, 2)},
        )

    return text


def check_article_quality(text: str) -> dict:
    """
    Return quality metadata about the article text (non-throwing).

    Useful for UI warnings rather than hard blocks.
    """
    word_count = len(text.split())
    char_count = len(text)
    is_recommended_length = char_count >= settings.RECOMMENDED_ARTICLE_LENGTH

    return {
        "word_count": word_count,
        "char_count": char_count,
        "is_recommended_length": is_recommended_length,
        "quality_warning": (
            None
            if is_recommended_length
            else f"Article is short ({char_count} chars). Recommended: {settings.RECOMMENDED_ARTICLE_LENGTH}+ chars for accurate analysis."
        ),
    }


# ---------------------------------------------------------------------------
# CSV / batch upload validation
# ---------------------------------------------------------------------------
VALID_TEXT_COLUMNS = {"text", "content", "article", "body", "headline", "title"}


def validate_csv_upload(df: pd.DataFrame, max_rows: int = 500) -> tuple[pd.DataFrame, str]:
    """
    Validate an uploaded CSV for batch processing.

    Returns (validated_df, text_column_name).
    Raises ValidationError on problems.
    """
    if df.empty:
        raise ValidationError("Uploaded CSV is empty.")

    if len(df) > max_rows:
        raise ValidationError(
            f"CSV contains {len(df)} rows. Maximum is {max_rows}.",
            details={"rows": len(df), "max_rows": max_rows},
        )

    # Find usable text column
    lower_cols = {c.lower().strip(): c for c in df.columns}
    text_col = None
    for candidate in VALID_TEXT_COLUMNS:
        if candidate in lower_cols:
            text_col = lower_cols[candidate]
            break

    if text_col is None:
        raise ValidationError(
            f"No suitable text column found. Expected one of: {sorted(VALID_TEXT_COLUMNS)}. "
            f"Found columns: {list(df.columns)}",
        )

    # Drop rows with empty text
    df = df.dropna(subset=[text_col])
    df = df[df[text_col].astype(str).str.strip().str.len() > 0]

    if df.empty:
        raise ValidationError("All rows in the CSV have empty text.")

    logger.info(
        "CSV validated",
        extra={"batch_size": len(df)},
    )
    return df, text_col


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------
def validate_url(url: str) -> str:
    """Validate and normalize a URL. Returns the URL or raises ValidationError."""
    if not url or not isinstance(url, str):
        raise ValidationError("URL must be a non-empty string.")

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    if not parsed.netloc or "." not in parsed.netloc:
        raise ValidationError(f"Invalid URL: {url}")

    return url
