"""
Session token storage tests — guards P1-1.

Session tokens used to be stored raw in ``sessions.token`` with a 7-day TTL, so
any read-only disclosure of that table (backup, log dump, unrelated SQLi) handed
the reader a working session for every logged-in user. Tokens are now stored as
SHA-256 hashes and looked up by hash.

These tests assert the property directly against the database rather than
through the API surface, because the API behaves identically either way — that
is exactly why the original bug went unnoticed.
"""
import hashlib
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api import app  # noqa: E402
from backend.db import get_db, ph  # noqa: E402

client = TestClient(app)

HEX = set("0123456789abcdef")

# Fixture credential for throwaway accounts in an ephemeral test DB — not a real
# secret. The pragma keeps the detect-secrets pre-commit hook quiet without
# widening its rules.
TEST_PASSWORD = "correct-horse-battery"  # pragma: allowlist secret


def _signup():
    """Create a throwaway account, return (token, user_id, email)."""
    email = f"session-test-{uuid.uuid4().hex[:12]}@example.com"
    r = client.post(
        "/api/v1/auth/signup",
        json={"name": "Session Test", "email": email, "password": TEST_PASSWORD},
    )
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    body = r.json()
    return body["token"], body["user"]["id"], email


def _session_rows(user_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(f"SELECT token, expires_at FROM sessions WHERE user_id = {ph()}", (user_id,))
        return c.fetchall()
    finally:
        conn.close()


class TestSessionTokenStorage:
    def test_token_stored_hashed_not_plaintext(self):
        token, user_id, _ = _signup()
        rows = _session_rows(user_id)
        assert len(rows) == 1, "signup should create exactly one session"
        stored = rows[0][0]

        assert stored != token, "session token is stored in plaintext"
        assert len(stored) == 64 and all(ch in HEX for ch in stored), (
            f"expected a 64-char sha256 hex digest, got {len(stored)} chars"
        )
        assert stored == hashlib.sha256(token.encode()).hexdigest()

    def test_login_also_stores_hashed(self):
        _, user_id, email = _signup()
        r = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": TEST_PASSWORD},
        )
        assert r.status_code == 200, r.text
        login_token = r.json()["token"]

        stored = {row[0] for row in _session_rows(user_id)}
        assert login_token not in stored, "login path stores the raw token"
        assert hashlib.sha256(login_token.encode()).hexdigest() in stored

    def test_returned_token_still_authenticates(self):
        """The hashing must be transparent to clients."""
        token, _, email = _signup()
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        assert r.json()["email"] == email

    def test_stored_value_is_not_itself_a_usable_token(self):
        """The core of the fix: leaking the table must not yield live sessions.

        An attacker with read access to ``sessions`` sees only the digest.
        Presenting it must fail, because lookup hashes the presented value
        (sha256 of the digest != the digest).
        """
        token, user_id, _ = _signup()
        stored = _session_rows(user_id)[0][0]
        assert stored != token  # sanity — otherwise this test proves nothing

        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {stored}"})
        assert r.status_code == 401, "the stored digest authenticated as a token"


class TestSessionLifecycle:
    def test_logout_deletes_the_session(self):
        token, user_id, _ = _signup()
        assert client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
        ).status_code == 200

        assert _session_rows(user_id) == [], "logout left the session row behind"
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, "token still works after logout"

    def test_expired_session_rejected_and_purged(self):
        token, user_id, _ = _signup()
        past = (datetime.now() - timedelta(days=1)).isoformat()
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                f"UPDATE sessions SET expires_at = {ph()} WHERE user_id = {ph()}",
                (past, user_id),
            )
            conn.commit()
        finally:
            conn.close()

        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, "expired session was accepted"
        assert _session_rows(user_id) == [], "expired session was not purged"

    @pytest.mark.parametrize("header", ["", "Bearer ", "Bearer not-a-real-token", "garbage"])
    def test_bad_tokens_rejected(self, header):
        r = client.get("/api/v1/auth/me", headers={"Authorization": header})
        assert r.status_code == 401


class TestPreHashMigration:
    def test_plaintext_row_cannot_authenticate(self):
        """A row written before the fix must be inert, not a working session.

        This is what makes the forced re-login safe: legacy plaintext rows do
        not authenticate even in the window before the purge migration runs.
        """
        _, user_id, _ = _signup()
        legacy = "legacy-plaintext-token-value"
        future = (datetime.now() + timedelta(days=7)).isoformat()
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                f"INSERT INTO sessions (token, user_id, expires_at) VALUES ({ph(3)})",
                (legacy, user_id, future),
            )
            conn.commit()
        finally:
            conn.close()

        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {legacy}"})
        assert r.status_code == 401, "a pre-hash plaintext session still authenticates"
