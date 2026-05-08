"""
GNews API client with caching, timeout, and structured error handling.
"""

import time
from typing import Dict, List, Optional, Tuple

import requests

from src.core.config import settings
from src.core.exceptions import GNewsAPIError
from src.core.logging_config import get_logger
from src.core.metrics import record_api_call

logger = get_logger(__name__)

GNEWS_SEARCH_URL = "https://gnews.io/api/v4/search"


class GNewsClient:
    """GNews API client with caching and quality filtering."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GNEWS_API_KEY
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "FakeNewsDetector/3.0"})
        self._status_cache: Optional[Tuple[bool, str, float]] = None  # (ok, msg, timestamp)
        self._STATUS_CACHE_TTL = 300  # 5 minutes

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def check_status(self) -> Tuple[bool, str, Dict]:
        """Check GNews API reachability. Results cached for 5 minutes."""
        now = time.time()
        if self._status_cache and (now - self._status_cache[2]) < self._STATUS_CACHE_TTL:
            return self._status_cache[0], self._status_cache[1], {}

        if not self.api_key:
            return False, "No GNEWS_API_KEY configured", {}
        try:
            resp = self._session.get(
                GNEWS_SEARCH_URL,
                params={"q": "test", "apikey": self.api_key, "max": 1, "lang": "en"},
                timeout=settings.GNEWS_TIMEOUT_SECONDS,
            )
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("totalArticles") or len(data.get("articles", []))
                msg = f"GNews reachable — articles found: {total}"
                self._status_cache = (True, msg, now)
                return True, msg, {"status_code": 200, "total": total}
            elif resp.status_code == 401:
                msg = "GNews 401 Unauthorized — API key invalid or expired"
                self._status_cache = (False, msg, now)
                return False, msg, {"status_code": 401}
            else:
                msg = f"GNews returned status {resp.status_code}"
                self._status_cache = (False, msg, now)
                return False, msg, {"status_code": resp.status_code}
        except requests.Timeout:
            return False, "GNews request timed out", {}
        except Exception as e:
            return False, f"GNews request failed: {e}", {}

    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for related news articles with quality filtering."""
        if not self.api_key:
            logger.warning("GNews search skipped — no API key")
            return []

        start = time.perf_counter()
        try:
            resp = self._session.get(
                GNEWS_SEARCH_URL,
                params={
                    "q": query, "apikey": self.api_key, "lang": "en",
                    "max": max_results, "sortby": "relevance",
                },
                timeout=settings.GNEWS_TIMEOUT_SECONDS,
            )
            latency_ms = (time.perf_counter() - start) * 1000

            if resp.status_code != 200:
                record_api_call("gnews", False, latency_ms)
                logger.warning(f"GNews search failed: HTTP {resp.status_code}")
                return []

            data = resp.json()
            articles = data.get("articles", []) if isinstance(data, dict) else []

            # Quality filter: must have title, source, and URL
            quality = [
                a for a in articles
                if a.get("title") and a.get("source", {}).get("name") and a.get("url")
            ]

            record_api_call("gnews", True, latency_ms)
            logger.info(f"GNews search returned {len(quality)} quality articles", extra={
                "api_name": "gnews", "latency_ms": round(latency_ms, 1),
            })
            return quality[:max_results]

        except requests.Timeout:
            record_api_call("gnews", False, (time.perf_counter() - start) * 1000)
            logger.error("GNews search timed out")
            return []
        except Exception as e:
            record_api_call("gnews", False, (time.perf_counter() - start) * 1000)
            logger.error(f"GNews search error: {e}")
            return []

    @staticmethod
    def calculate_web_score(articles: List[Dict], had_keywords: bool) -> float:
        """Calculate web verification score from search results."""
        if articles and len(articles) >= 3:
            return 0.7
        if articles and len(articles) >= 1:
            return 0.6
        # No articles found — treat as neutral, not suspicious.
        # Absence of corroboration is NOT evidence of fakeness; it could be
        # bad keywords, a niche topic, or a very recent story.
        return 0.5

