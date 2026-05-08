"""
Gemini AI client with retry, timeout, and structured error handling.
"""

import time
from typing import Optional

from src.core.config import settings
from src.core.exceptions import GeminiAPIError
from src.core.logging_config import get_logger
from src.core.metrics import record_api_call

logger = get_logger(__name__)

# Prompt versioning — change the version when modifying prompts
FACT_CHECK_PROMPT_VERSION = "v2.0"

FACT_CHECK_PROMPT = """You are an expert media analyst evaluating whether a news article exhibits characteristics of legitimate journalism or misinformation/fabrication.

ARTICLE:
{article_text}

EVALUATE THE WRITING QUALITY AND JOURNALISTIC STANDARDS:
1. Writing style - Does it follow professional journalistic conventions (inverted pyramid, neutral tone, proper attribution)?
2. Source attribution - Are claims attributed to named officials, organizations, or documents?
3. Specificity - Does it include specific dates, names, locations, and verifiable details?
4. Tone and language - Is the tone neutral and factual, or sensationalized and emotionally manipulative?
5. Logical coherence - Is the narrative logically consistent and well-structured?
6. Red flags - Look for: anonymous unverifiable sources, conspiracy language, extreme exaggeration, clickbait patterns, ALL CAPS, excessive exclamation marks, or fabricated quotes.

IMPORTANT GUIDELINES:
- Recent or current events should NOT be penalized simply for being new. Evaluate the WRITING QUALITY, not whether you can personally verify the events.
- Articles from wire services (AP, Reuters, AFP) or major outlets naturally follow professional patterns — recognize these patterns.
- Focus on HOW the article is written, not WHETHER the specific claims are in your training data.

PROVIDE YOUR ASSESSMENT AS:
- CREDIBILITY LEVEL: HIGH / MEDIUM / LOW
- KEY FINDINGS: (3-5 bullet points about writing quality indicators)
- VERDICT: LIKELY_TRUE / MIXED / LIKELY_FALSE / UNVERIFIABLE
- CONFIDENCE: 0-100%"""

TRANSLATION_PROMPT = """Translate the following text to {target_lang}.
Return ONLY the translated text, no explanations.

Text:
{text}"""


class GeminiClient:
    """Wrapper around Google Generative AI with retry and metrics."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self._model = None
        self._available = False
        self._initialize()

    def _initialize(self):
        if not self.api_key:
            logger.info("Gemini API key not configured — AI verification disabled")
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
            self._available = True
            logger.info("Gemini client initialized successfully")
        except ImportError:
            logger.warning("google-generativeai not installed — AI verification disabled")
        except Exception as e:
            logger.error(f"Gemini initialization failed: {e}")

    @property
    def is_available(self) -> bool:
        return self._available

    def verify_claim(self, text: str, max_chars: int = 2000) -> Optional[str]:
        """Fact-check an article using Gemini AI. Returns analysis text or None."""
        if not self._available:
            return None
        start = time.perf_counter()
        try:
            prompt = FACT_CHECK_PROMPT.format(article_text=text[:max_chars])
            response = self._model.generate_content(prompt)
            latency_ms = (time.perf_counter() - start) * 1000
            record_api_call("gemini", True, latency_ms)
            logger.info("Gemini verification complete", extra={"latency_ms": round(latency_ms, 1), "api_name": "gemini"})
            return response.text
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            record_api_call("gemini", False, latency_ms)
            logger.error(f"Gemini API error: {e}", extra={"api_name": "gemini"})
            raise GeminiAPIError(f"Gemini verification failed: {e}") from e

    def translate_text(self, text: str, target_lang: str = "en", max_chars: int = 1000) -> Optional[str]:
        """Translate text using Gemini. Returns translated text or None."""
        if not self._available:
            return None
        try:
            prompt = TRANSLATION_PROMPT.format(target_lang=target_lang, text=text[:max_chars])
            response = self._model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini translation failed: {e}")
            return None

    @staticmethod
    def parse_verdict(gemini_response: str) -> float:
        """Parse Gemini response into a credibility score (0.0 to 1.0).
        
        Extracts the VERDICT and CREDIBILITY lines specifically rather than
        doing naive substring matching on the entire response (which would
        match 'FALSE' inside phrases like 'no false claims detected').
        """
        if not gemini_response:
            return 0.5

        upper = gemini_response.upper()

        # --- Step 1: Try to extract the VERDICT line specifically ---
        verdict_line = ""
        credibility_line = ""
        for line in upper.split("\n"):
            stripped = line.strip().lstrip("-* ")
            if stripped.startswith("VERDICT"):
                verdict_line = stripped
            elif stripped.startswith("CREDIBILITY"):
                credibility_line = stripped

        # --- Step 2: Parse VERDICT line (most reliable signal) ---
        if verdict_line:
            # Check positive verdicts FIRST
            if "LIKELY_TRUE" in verdict_line or "LIKELY TRUE" in verdict_line:
                return 0.8
            if "LIKELY_FALSE" in verdict_line or "LIKELY FALSE" in verdict_line:
                return 0.2
            if "MIXED" in verdict_line or "UNCERTAIN" in verdict_line:
                return 0.5
            if "UNVERIFIABLE" in verdict_line:
                return 0.5  # Unverifiable ≠ fake, treat as neutral
            # Generic TRUE/FALSE only on the verdict line
            if "TRUE" in verdict_line:
                return 0.75
            if "FALSE" in verdict_line or "FAKE" in verdict_line:
                return 0.25

        # --- Step 3: Fall back to CREDIBILITY line ---
        if credibility_line:
            if "HIGH" in credibility_line:
                return 0.8
            if "LOW" in credibility_line:
                return 0.25
            if "MEDIUM" in credibility_line:
                return 0.5

        # --- Step 4: Last resort — scan full response for strong signals ---
        # Only look for very specific complete phrases, not bare "FALSE"
        if "CREDIBILITY LEVEL: HIGH" in upper or "CREDIBILITY: HIGH" in upper:
            return 0.8
        if "CREDIBILITY LEVEL: LOW" in upper or "CREDIBILITY: LOW" in upper:
            return 0.25

        return 0.5  # Default to neutral when we can't parse

