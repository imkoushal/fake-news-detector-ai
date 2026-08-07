"""
Authentication helpers — password hashing, token management, user lookup.
"""
import re
import hashlib
import logging
import bcrypt
import secrets
from datetime import datetime, timedelta, timezone

from backend.db import get_db, ph

logger = logging.getLogger("fake_news_api")

# Session token TTL (7 days)
SESSION_TTL_DAYS = 7


def hash_session_token(token: str) -> str:
    """Hash a session token for storage and lookup.

    Plain SHA-256 rather than bcrypt is deliberate here. The token is 256 bits
    of CSPRNG output, so it is not guessable and gains nothing from a slow KDF
    or a per-row salt. The only property we need is one-wayness: a read-only
    disclosure of the sessions table (a backup, a log dump, an unrelated SQLi)
    must not hand the reader a working session for every logged-in user.

    Always store and query the output of this function — never the plaintext.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def new_session_token() -> tuple[str, str]:
    """Mint a session token.

    Returns ``(plaintext, hashed)``. Return the plaintext to the client exactly
    once; persist only the hash. The two are deliberately returned together so
    a call site cannot accidentally store the wrong one.
    """
    token = secrets.token_urlsafe(32)
    return token, hash_session_token(token)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (salt is embedded in the output)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, stored_hash: str, stored_salt: str = "") -> bool:
    """Verify a password against its hash.
    Supports both bcrypt (new) and legacy SHA-256 (old) hashes.
    """
    if stored_salt == "bcrypt" or stored_hash.startswith("$2b$"):
        # Modern bcrypt hash
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    else:
        # Legacy SHA-256 fallback — needed until all users re-login
        import hashlib
        legacy = hashlib.sha256((stored_salt + password).encode()).hexdigest()
        return legacy == stored_hash


def sanitize_preview(text: str, max_len: int = 200) -> str:
    """Unicode-safe text preview sanitizer.
    Strips control characters but preserves accented letters, quotes, and international text.
    """
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized[:max_len]


def get_user_from_token(request) -> int | None:
    """Extract user_id from auth token. Rejects expired tokens."""
    auth_header = request.headers.get("Authorization", "").strip()
    # Strip the "Bearer " scheme prefix only (case-insensitive), not any occurrence.
    if auth_header[:7].lower() == "bearer ":
        token = auth_header[7:].strip()
    else:
        token = auth_header
    if not token:
        return None
    # Sessions are stored hashed — look up by hash, never by the presented value.
    token_hash = hash_session_token(token)
    conn = get_db()
    c = conn.cursor()
    c.execute(f"SELECT user_id, expires_at FROM sessions WHERE token = {ph()}", (token_hash,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    # Check expiry — fail closed: any unparseable/invalid expiry is treated as expired.
    if row[1]:
        expired = False
        try:
            exp = datetime.fromisoformat(str(row[1]))
            # Compare using a matching aware/naive "now" so a tz-aware DB timestamp
            # (PostgreSQL) doesn't raise and get silently accepted.
            now = datetime.now(timezone.utc) if exp.tzinfo else datetime.now()
            expired = now > exp
        except (ValueError, TypeError):
            expired = True
        if expired:
            c.execute(f"DELETE FROM sessions WHERE token = {ph()}", (token_hash,))
            conn.commit()
            conn.close()
            return None
    conn.close()
    return row[0]


def create_session(user_id: int) -> str:
    """Create a new session for a user and return the plaintext token.

    Only the hash reaches the database; the plaintext is returned to the caller
    and is unrecoverable afterwards.
    """
    token, token_hash = new_session_token()
    expires = datetime.now() + timedelta(days=SESSION_TTL_DAYS)
    from backend.db import execute_db
    execute_db(
        f"INSERT INTO sessions (token, user_id, expires_at) VALUES ({ph(3)})",
        (token_hash, user_id, expires.isoformat()),
        commit=True
    )
    return token
