"""
Shared async HTTP client — replaces blocking `requests` calls (H1 fix).
Uses httpx.AsyncClient with connection pooling and timeouts.
"""
import httpx
import logging

logger = logging.getLogger("fake_news_api")

# Shared client with connection pooling (created lazily, closed on shutdown)
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Get the shared async HTTP client (lazy initialization)."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
        )
    return _client


async def close_client():
    """Close the shared client (call on app shutdown)."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None
        logger.info("Async HTTP client closed")
