"""
Custom exception hierarchy for the Fake News Detector.

All application-specific exceptions derive from FakeNewsDetectorError
so callers can catch the base class or specific subclasses.
"""


class FakeNewsDetectorError(Exception):
    """Base exception for all Fake News Detector errors."""

    def __init__(self, message: str = "", *, details: dict | None = None):
        self.details = details or {}
        super().__init__(message)


# ---------------------------------------------------------------------------
# Model layer
# ---------------------------------------------------------------------------
class ModelLoadError(FakeNewsDetectorError):
    """Raised when a model artifact cannot be loaded from disk."""


class PredictionError(FakeNewsDetectorError):
    """Raised when model prediction fails (corrupt input, shape mismatch, etc.)."""


class ModelNotLoadedError(FakeNewsDetectorError):
    """Raised when prediction is attempted but no model is loaded."""


# ---------------------------------------------------------------------------
# External services
# ---------------------------------------------------------------------------
class ExternalAPIError(FakeNewsDetectorError):
    """Raised when an external API (GNews, Gemini) call fails."""


class GNewsAPIError(ExternalAPIError):
    """Raised specifically for GNews API failures."""


class GeminiAPIError(ExternalAPIError):
    """Raised specifically for Gemini API failures."""


class ExternalAPITimeoutError(ExternalAPIError):
    """Raised when an external API call exceeds timeout."""


# ---------------------------------------------------------------------------
# Data / validation
# ---------------------------------------------------------------------------
class ValidationError(FakeNewsDetectorError):
    """Raised when input validation fails (too short, bad encoding, etc.)."""


class ArticleTooShortError(ValidationError):
    """Article text is below the minimum required length."""


class ArticleTooLongError(ValidationError):
    """Article text exceeds the maximum allowed length."""


class UnsupportedLanguageError(ValidationError):
    """Article language is not supported for analysis."""


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
class DatabaseError(FakeNewsDetectorError):
    """Raised when a database operation fails."""


class DatabaseConnectionError(DatabaseError):
    """Raised when the database connection cannot be established."""


class DatabaseMigrationError(DatabaseError):
    """Raised when a database migration fails."""


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------
class PreprocessingError(FakeNewsDetectorError):
    """Raised when text preprocessing fails."""
