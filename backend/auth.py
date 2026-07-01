"""
Authentication helpers — password hashing, token management, user lookup.
"""
import re
import logging
import bcrypt
import secrets
from datetime import datetime, timedelta

from backend.db import get_db, ph

logger = logging.getLogger("fake_news_api")

# Session token TTL (7 days)
SESSION_TTL_DAYS = 7


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
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return None
    conn = get_db()
    c = conn.cursor()
    c.execute(f"SELECT user_id, expires_at FROM sessions WHERE token = {ph()}", (token,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    # Check expiry
    if row[1]:
        try:
            exp = datetime.fromisoformat(str(row[1]))
            if datetime.now() > exp:
                # Token expired — clean it up
                c.execute(f"DELETE FROM sessions WHERE token = {ph()}", (token,))
                conn.commit()
                conn.close()
                return None
        except (ValueError, TypeError):
            pass
    conn.close()
    return row[0]


def create_session(user_id: int) -> str:
    """Create a new session token for a user, returns the token string."""
    token = secrets.token_hex(32)
    expires = datetime.now() + timedelta(days=SESSION_TTL_DAYS)
    from backend.db import execute_db
    execute_db(
        f"INSERT INTO sessions (token, user_id, expires_at) VALUES ({ph(3)})",
        (token, user_id, expires.isoformat()),
        commit=True
    )
    return token
