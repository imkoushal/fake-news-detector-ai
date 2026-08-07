"""
Tests for backend/ package — covers cache, auth, ssrf, db, and http_client.
Replaces the 5 deleted test_*.py files that imported the removed src/ package.
"""
import pytest
import time
import hashlib
import threading
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


# ── Cache Tests ──

class TestClaimCache:
    """Tests for backend/cache.py — thread-safe TTL-based LRU cache."""

    def setup_method(self):
        from backend.cache import ClaimCache
        self.cache = ClaimCache(max_size=3, ttl_seconds=2)

    def test_set_and_get(self):
        self.cache.set("hello world", "test-endpoint", {"score": 0.9})
        result = self.cache.get("hello world", "test-endpoint")
        assert result is not None
        assert result["score"] == 0.9

    def test_miss_returns_none(self):
        result = self.cache.get("nonexistent", "test-endpoint")
        assert result is None

    def test_different_endpoints_different_keys(self):
        self.cache.set("same text", "endpoint-a", {"val": "a"})
        self.cache.set("same text", "endpoint-b", {"val": "b"})
        assert self.cache.get("same text", "endpoint-a")["val"] == "a"
        assert self.cache.get("same text", "endpoint-b")["val"] == "b"

    def test_ttl_expiration(self):
        self.cache.set("expiring", "test", {"data": 1})
        assert self.cache.get("expiring", "test") is not None
        time.sleep(2.1)
        assert self.cache.get("expiring", "test") is None

    def test_max_size_eviction(self):
        """Oldest entries evicted when cache exceeds max_size."""
        self.cache.set("first", "e", {"n": 1})
        self.cache.set("second", "e", {"n": 2})
        self.cache.set("third", "e", {"n": 3})
        self.cache.set("fourth", "e", {"n": 4})  # should evict "first"
        assert self.cache.get("first", "e") is None
        assert self.cache.get("fourth", "e")["n"] == 4

    def test_returns_copy_not_reference(self):
        """Mutation of returned dict must not affect cached data."""
        self.cache.set("immutable", "e", {"list": [1, 2, 3]})
        result = self.cache.get("immutable", "e")
        result["list"].append(999)
        fresh = self.cache.get("immutable", "e")
        assert fresh["list"] == [1, 2, 3], "Cache should return deep copies"

    def test_stats(self):
        self.cache.get("miss1", "e")
        self.cache.set("hit1", "e", {"x": 1})
        self.cache.get("hit1", "e")
        stats = self.cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["cache_size"] == 1

    def test_clear(self):
        self.cache.set("a", "e", {"x": 1})
        self.cache.clear()
        assert self.cache.get("a", "e") is None
        assert self.cache.stats()["cache_size"] == 0

    def test_thread_safety(self):
        """Concurrent access should not raise or corrupt data."""
        errors = []

        def writer(n):
            try:
                for i in range(50):
                    self.cache.set(f"key-{n}-{i}", "e", {"v": i})
            except Exception as ex:
                errors.append(ex)

        def reader():
            try:
                for _ in range(50):
                    self.cache.get("key-0-0", "e")
            except Exception as ex:
                errors.append(ex)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
        threads += [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0


# ── SSRF Tests ──

class TestSSRFProtection:
    """Tests for backend/ssrf.py — URL validation against private IPs."""

    def test_blocks_localhost(self):
        from backend.ssrf import validate_url
        with pytest.raises(ValueError, match="Blocked hostname"):
            validate_url("http://localhost/secret")

    def test_blocks_metadata_endpoint(self):
        from backend.ssrf import validate_url
        with pytest.raises(ValueError, match="Blocked hostname"):
            validate_url("http://metadata.google.internal/computeMetadata/v1/")

    def test_blocks_private_ip(self):
        from backend.ssrf import validate_url
        with pytest.raises(ValueError):
            validate_url("http://192.168.1.1/admin")

    def test_blocks_loopback(self):
        from backend.ssrf import validate_url
        with pytest.raises(ValueError):
            validate_url("http://127.0.0.1:8080/")

    def test_blocks_non_http_schemes(self):
        from backend.ssrf import validate_url
        with pytest.raises(ValueError, match="Only http"):
            validate_url("ftp://example.com/file")
        with pytest.raises(ValueError, match="Only http"):
            validate_url("file:///etc/passwd")

    def test_allows_public_urls(self):
        from backend.ssrf import validate_url
        result = validate_url("https://www.google.com")
        assert result == "https://www.google.com"

    def test_blocks_aws_metadata(self):
        from backend.ssrf import validate_url
        with pytest.raises(ValueError):
            validate_url("http://169.254.169.254/latest/meta-data/")


class TestSSRFPortRestriction:
    """Guards P1-4 — a public hostname on a non-web port used to pass.

    These run offline: the port check is evaluated before DNS resolution, so no
    lookup happens for a rejected port.
    """

    @pytest.mark.parametrize("url", [
        "http://example.com:22/",       # SSH — turns the fetcher into a port scanner
        "http://example.com:3306/",     # MySQL
        "http://example.com:6379/",     # Redis
        "http://example.com:25/",       # SMTP
        "https://example.com:5432/",    # PostgreSQL
    ])
    def test_blocks_non_web_ports(self, url):
        from backend.ssrf import validate_url
        with pytest.raises(ValueError, match="not allowed"):
            validate_url(url)

    def test_blocks_malformed_port(self):
        from backend.ssrf import validate_url
        with pytest.raises(ValueError, match="invalid port"):
            validate_url("http://example.com:notaport/")

    def test_allows_web_ports(self):
        """Explicit web ports must still pass the port gate.

        Asserted by absence of a port error rather than overall success, so the
        test does not depend on DNS resolving example.com.
        """
        from backend.ssrf import validate_url
        for url in ["http://example.com:80/", "https://example.com:443/",
                    "http://example.com:8080/", "https://example.com:8443/"]:
            try:
                validate_url(url)
            except ValueError as e:
                assert "not allowed" not in str(e), f"{url} rejected on port: {e}"

    def test_http_url_resolves_against_port_80_not_443(self, monkeypatch):
        """Regression: the default was a hardcoded 443 even for http:// URLs.

        getaddrinfo was therefore called with the wrong port for every plain-http
        URL — harmless for A-record lookups but wrong, and it meant the port the
        code reasoned about was not the port the URL named.
        """
        import backend.ssrf as ssrf_mod
        seen = {}

        def fake_getaddrinfo(host, port, **kwargs):
            seen["port"] = port
            return [(2, 1, 6, "", ("93.184.216.34", port))]

        monkeypatch.setattr(ssrf_mod.socket, "getaddrinfo", fake_getaddrinfo)
        ssrf_mod.validate_url("http://example.com/article")
        assert seen["port"] == 80

        ssrf_mod.validate_url("https://example.com/article")
        assert seen["port"] == 443


class TestSSRFRedirectRevalidation:
    """Guards the redirect bypass: a public URL that 30x-es to an internal one."""

    @pytest.fixture(autouse=True)
    def _stub_dns(self, monkeypatch):
        """Resolve offline so these assert on SSRF logic, not on the network.

        Literal IPs pass through unchanged (so the metadata address is still
        judged on its real value); any hostname maps to a public IP.
        """
        import ipaddress as _ip
        import backend.ssrf as ssrf_mod

        def fake_getaddrinfo(host, port, **kwargs):
            try:
                addr = str(_ip.ip_address(host))
            except ValueError:
                addr = "93.184.216.34"   # public, non-blocked
            return [(2, 1, 6, "", (addr, port))]

        monkeypatch.setattr(ssrf_mod.socket, "getaddrinfo", fake_getaddrinfo)

    class _FakeResponse:
        def __init__(self, status_code, headers=None):
            self.status_code = status_code
            self.headers = headers or {}

    class _FakeClient:
        """Minimal stand-in for httpx.AsyncClient — no network, no DNS."""
        def __init__(self, script):
            self.script = script       # url -> _FakeResponse
            self.requested = []

        async def get(self, url, headers=None, follow_redirects=False):
            self.requested.append(url)
            return self.script[url]

    def test_redirect_to_metadata_ip_is_blocked(self):
        import asyncio
        from backend.ssrf import safe_get

        start = "https://example.com/news"
        client = self._FakeClient({
            start: self._FakeResponse(302, {"location": "http://169.254.169.254/latest/meta-data/"}),
        })

        with pytest.raises(ValueError, match="blocked IP range"):
            asyncio.run(safe_get(client, start))

        assert client.requested == [start], "the redirect target was fetched anyway"

    def test_redirect_to_blocked_port_is_blocked(self):
        import asyncio
        from backend.ssrf import safe_get

        start = "https://example.com/news"
        client = self._FakeClient({
            start: self._FakeResponse(302, {"location": "http://example.com:22/"}),
        })

        with pytest.raises(ValueError, match="not allowed"):
            asyncio.run(safe_get(client, start))

    def test_redirect_limit_enforced(self):
        import asyncio
        from backend.ssrf import safe_get

        start = "https://example.com/a"
        client = self._FakeClient({
            start: self._FakeResponse(302, {"location": "https://example.com/a"}),
        })
        with pytest.raises(ValueError, match="Too many redirects"):
            asyncio.run(safe_get(client, start, max_redirects=2))


# ── Auth Helper Tests ──

class TestAuthHelpers:
    """Tests for backend/auth.py — password hashing, sanitization."""

    def test_hash_and_verify_bcrypt(self):
        from backend.auth import hash_password, verify_password
        pw = "MyS3cur3P@ss!"
        hashed = hash_password(pw)
        assert hashed.startswith("$2b$")
        assert verify_password(pw, hashed, "bcrypt")

    def test_wrong_password_fails(self):
        from backend.auth import hash_password, verify_password
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed, "bcrypt")

    def test_legacy_sha256_verify(self):
        """Legacy SHA-256 hashes should still verify correctly."""
        from backend.auth import verify_password
        salt = "test_salt"
        password = "old_password"
        legacy_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        assert verify_password(password, legacy_hash, salt)
        assert not verify_password("wrong", legacy_hash, salt)

    def test_sanitize_preview(self):
        from backend.auth import sanitize_preview
        # Strips control characters
        assert "\x00" not in sanitize_preview("Hello\x00World")
        # Preserves normal text
        assert sanitize_preview("Normal text") == "Normal text"
        # Respects max_len
        assert len(sanitize_preview("x" * 500, max_len=100)) == 100
        # Collapses whitespace
        assert sanitize_preview("too   many    spaces") == "too many spaces"


# ── DB Helper Tests ──

class TestDBHelpers:
    """Tests for backend/db.py — placeholder generation."""

    def test_ph_single(self):
        from backend.db import ph
        result = ph(1)
        assert result in ("?", "%s")  # depends on SQLite vs Postgres

    def test_ph_multiple(self):
        from backend.db import ph
        result = ph(3)
        parts = result.split(", ")
        assert len(parts) == 3

    def test_execute_db_returns_none_by_default(self):
        """execute_db with fetch='none' should return None."""
        from backend.db import execute_db
        # This will create a table if it doesn't exist — safe idempotent operation
        result = execute_db(
            "CREATE TABLE IF NOT EXISTS _test_exec (id INTEGER PRIMARY KEY)",
            commit=True
        )
        assert result is None


# ── HTTP Client Tests ──

class TestHTTPClient:
    """Tests for backend/http_client.py — shared async client."""

    def test_get_client_returns_client(self):
        from backend.http_client import get_client
        import httpx
        client = get_client()
        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed

    def test_get_client_singleton(self):
        from backend.http_client import get_client
        c1 = get_client()
        c2 = get_client()
        assert c1 is c2

    def test_close_client(self):
        from backend.http_client import get_client, close_client
        import asyncio
        client = get_client()
        assert not client.is_closed
        asyncio.run(close_client())
        # After close, get_client should create a new one
        client2 = get_client()
        assert not client2.is_closed
