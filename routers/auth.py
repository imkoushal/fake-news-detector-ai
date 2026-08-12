"""
Auth router — signup, login, logout, /me, Google OAuth.
Extracted from api.py as part of P3-3 router split.
"""
import os
import logging
import secrets
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict

from backend.db import get_db, ph, USE_POSTGRES
from backend.auth import (
    hash_password as _hash_password,
    verify_password as _verify_password,
    get_user_from_token as _get_user_from_token,
    new_session_token as _new_session_token,
    hash_session_token as _hash_session_token,
    SESSION_TTL_DAYS,
)
from backend import metrics as _metrics

logger = logging.getLogger("fake_news_api")

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

# ── Login brute-force lockout ──
# Per-email failed-attempt tracker. Complements the IP-based slowapi limit:
# slowapi caps request *rate*, this locks a targeted *account* after repeated
# failures regardless of how the attacker rotates IPs.
# NOTE: in-memory + per-process. Fine for the current single-instance Render
# deployment (resets on restart); move to Redis/DB if scaled horizontally.
_failed_logins: dict = defaultdict(list)  # email -> [unix_ts, ...]
LOGIN_MAX_FAILURES = 5      # failures within the window before lockout
LOGIN_FAIL_WINDOW = 900     # 15 min sliding window (seconds)
LOGIN_LOCKOUT_SECS = 900    # lock duration after threshold reached


def _login_locked(email: str) -> bool:
    """True if this email is currently locked out; prunes stale entries."""
    now = datetime.now().timestamp()
    recent = [t for t in _failed_logins.get(email, []) if now - t < LOGIN_LOCKOUT_SECS]
    _failed_logins[email] = recent
    return len(recent) >= LOGIN_MAX_FAILURES


def _record_login_failure(email: str) -> None:
    now = datetime.now().timestamp()
    recent = [t for t in _failed_logins.get(email, []) if now - t < LOGIN_FAIL_WINDOW]
    recent.append(now)
    _failed_logins[email] = recent


def _clear_login_failures(email: str) -> None:
    _failed_logins.pop(email, None)


# ── Pydantic Models ──
class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str  # The ID token from Google Identity Services


# ── Google OAuth config ──
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


# Migration: add google_id and avatar_url columns if missing
def migrate_google_columns():
    try:
        _conn = get_db()
        _c = _conn.cursor()
        try:
            _c.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
            logger.info("Migrated users table: added google_id column")
        except Exception:
            pass
        try:
            _c.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
            logger.info("Migrated users table: added avatar_url column")
        except Exception:
            pass
        _conn.commit()
        _conn.close()
    except Exception as e:
        logger.warning(f"Google auth migration skipped: {e}")


# ── Auth Endpoints ──

@router.post("/signup")
async def signup(req: SignupRequest, request: Request):
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if len(req.name.strip()) < 1:
        raise HTTPException(400, "Name is required")

    # ── P3-1 FIX: bcrypt hashing (~100ms) + DB writes off the event loop ──
    def _signup_sync():
        salt = "bcrypt"  # Marker — bcrypt embeds its own salt in the hash
        pw_hash = _hash_password(req.password)

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                f"INSERT INTO users (name, email, password_hash, salt) VALUES ({ph(4)})",
                (req.name.strip(), req.email.strip().lower(), pw_hash, salt)
            )
            if USE_POSTGRES:
                c.execute("SELECT currval(pg_get_serial_sequence('users','id'))")
                user_id = c.fetchone()[0]
            else:
                user_id = c.lastrowid
            # Store the hash, hand the plaintext to the client (see backend/auth.py).
            token, token_hash = _new_session_token()
            expires_at = (datetime.now() + timedelta(days=SESSION_TTL_DAYS)).isoformat()
            c.execute(f"INSERT INTO sessions (token, user_id, expires_at) VALUES ({ph(3)})", (token_hash, user_id, expires_at))
            conn.commit()
            _metrics.log_event(_metrics.EVENT_SIGNUP, user_id=user_id, source="web", meta={"method": "password"})
            return {
                "token": token,
                "user": {"id": user_id, "name": req.name.strip(), "email": req.email.strip().lower()}
            }
        except Exception as e:
            conn.rollback()
            err = str(e).lower()
            if "unique" in err or "duplicate" in err:
                raise HTTPException(409, "An account with this email already exists")
            logger.error(f"Signup error: {e}")
            raise HTTPException(500, "Account creation failed. Please try again.")
        finally:
            conn.close()

    return await run_in_threadpool(_signup_sync)


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    email_key = req.email.strip().lower()
    # Finding #3: account lockout after repeated failures for this email.
    if _login_locked(email_key):
        logger.warning(f"Login blocked — account locked out: {email_key}")
        raise HTTPException(
            429,
            "Too many failed login attempts. Try again in 15 minutes.",
        )
    # ── P3-1 FIX: bcrypt verify (~100ms) + DB lookups off the event loop ──
    def _login_sync():
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                f"SELECT id, name, email, password_hash, salt FROM users WHERE email = {ph()}",
                (email_key,)
            )
            user = c.fetchone()
            if not user:
                # M5 FIX: Dummy bcrypt hash to prevent timing-based user enumeration
                _hash_password("dummy-password-for-constant-time")
                _record_login_failure(email_key)
                raise HTTPException(401, "Invalid email or password")
            if not _verify_password(req.password, user[3], user[4]):
                _record_login_failure(email_key)
                raise HTTPException(401, "Invalid email or password")

            # Successful auth — clear the failure counter for this account.
            _clear_login_failures(email_key)

            # Auto-upgrade legacy SHA-256 hashes to bcrypt on successful login
            # Commit upgrade immediately so it persists even if session creation fails
            if user[4] != "bcrypt" and not user[3].startswith("$2b$"):
                logger.warning(f"Legacy SHA-256 hash detected for user {user[0]} — auto-upgrading to bcrypt. Consider prompting this user to change their password.")
                new_hash = _hash_password(req.password)
                c.execute(
                    f"UPDATE users SET password_hash = {ph()}, salt = {ph()} WHERE id = {ph()}",
                    (new_hash, "bcrypt", user[0])
                )
                conn.commit()  # Commit hash upgrade independently
                logger.info(f"Auto-upgraded password hash to bcrypt for user {user[0]}")

            token, token_hash = _new_session_token()
            expires_at = (datetime.now() + timedelta(days=SESSION_TTL_DAYS)).isoformat()
            c.execute(f"INSERT INTO sessions (token, user_id, expires_at) VALUES ({ph(3)})", (token_hash, user[0], expires_at))
            conn.commit()
            return {"token": token, "user": {"id": user[0], "name": user[1], "email": user[2]}}
        finally:
            conn.close()

    return await run_in_threadpool(_login_sync)


@router.get("/me")
async def get_me(request: Request):
    # Resolve via the shared helper so expiry is enforced (and expired
    # sessions are purged) — consistent with every other authed endpoint.
    # ── P3-1 FIX: dispatch sync auth + DB to threadpool ──
    def _get_me_sync():
        user_id = _get_user_from_token(request)
        if not user_id:
            raise HTTPException(401, "Invalid session")
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                f"SELECT id, name, email, avatar_url FROM users WHERE id = {ph()}",
                (user_id,)
            )
            user = c.fetchone()
            if not user:
                raise HTTPException(401, "Invalid session")
            return {"id": user[0], "name": user[1], "email": user[2], "avatar_url": user[3] or ""}
        finally:
            conn.close()

    return await run_in_threadpool(_get_me_sync)


@router.post("/logout")
async def logout(request: Request):
    # Strip the scheme prefix the same way get_user_from_token does. The two
    # must agree exactly: the value is hashed before lookup, so any
    # divergence turns logout into a silent no-op that leaves the session live.
    auth_header = request.headers.get("Authorization", "").strip()
    token = auth_header[7:].strip() if auth_header[:7].lower() == "bearer " else auth_header
    if token:
        # ── P3-1 FIX: dispatch sync DB delete to threadpool ──
        def _logout_sync():
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute(f"DELETE FROM sessions WHERE token = {ph()}", (_hash_session_token(token),))
                conn.commit()
            except Exception as e:
                logger.error(f"Logout session cleanup failed: {e}")
                conn.rollback()
            finally:
                conn.close()
        await run_in_threadpool(_logout_sync)
    return {"ok": True}


@router.post("/google")
async def google_auth(req: GoogleAuthRequest, request: Request):
    """Authenticate via Google Sign-In.
    C1 FIX: Verifies JWT signature cryptographically using google-auth library.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(500, "Google OAuth is not configured on this server")

    # C1 FIX: Cryptographic JWT verification (replaces insecure base64 decode)
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        payload = google_id_token.verify_oauth2_token(
            req.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ImportError:
        # SECURITY FIX: Do NOT fall back to manual base64 JWT decode without
        # signature verification — any attacker could forge a valid-looking token.
        # Require google-auth to be installed for Google OAuth to work.
        logger.error("google-auth library is not installed — Google OAuth is unavailable. "
                     "Install with: pip install google-auth")
        raise HTTPException(
            503,
            "Google Sign-In is temporarily unavailable. Please use email/password login."
        )
    except ValueError as e:
        logger.error(f"Google token verification failed: {e}")
        raise HTTPException(401, "Invalid Google credential")

    google_id = payload.get("sub")
    email = payload.get("email", "").lower()
    name = payload.get("name", email.split("@")[0])
    avatar_url = payload.get("picture", "")

    if not email or not google_id:
        raise HTTPException(401, "Google token missing required fields")

    conn = get_db()
    c = conn.cursor()
    try:
        # Check if user exists by google_id or email
        c.execute(f"SELECT id, name, email, avatar_url FROM users WHERE email = {ph()}", (email,))
        user = c.fetchone()
        is_new_user = user is None

        if user:
            # Existing user — update google_id and avatar if not set
            user_id, user_name, user_email = user[0], user[1], user[2]
            c.execute(
                f"UPDATE users SET google_id = {ph()}, avatar_url = {ph()} WHERE id = {ph()}",
                (google_id, avatar_url, user_id)
            )
        else:
            # New user — create account with a random password (they'll only use Google login)
            random_pw_hash = _hash_password(secrets.token_urlsafe(32))
            c.execute(
                f"INSERT INTO users (name, email, password_hash, salt, google_id, avatar_url) VALUES ({ph(6)})",
                (name, email, random_pw_hash, "bcrypt", google_id, avatar_url)
            )
            if USE_POSTGRES:
                c.execute("SELECT currval(pg_get_serial_sequence('users','id'))")
                user_id = c.fetchone()[0]
            else:
                user_id = c.lastrowid
            user_name = name
            user_email = email

        # Create session
        token, token_hash = _new_session_token()
        expires_at = (datetime.now() + timedelta(days=SESSION_TTL_DAYS)).isoformat()
        c.execute(f"INSERT INTO sessions (token, user_id, expires_at) VALUES ({ph(3)})", (token_hash, user_id, expires_at))
        conn.commit()
        if is_new_user:
            _metrics.log_event(_metrics.EVENT_SIGNUP, user_id=user_id, source="web", meta={"method": "google"})

        return {
            "token": token,
            "user": {
                "id": user_id,
                "name": user_name,
                "email": user_email,
                "avatar_url": avatar_url
            }
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Google auth failed: {e}")
        raise HTTPException(500, "Google authentication failed")
    finally:
        conn.close()


# Expose Google Client ID to frontend (never expose the secret, only the public client ID)
@router.get("/google-client-id")
async def get_google_client_id():
    return {"client_id": GOOGLE_CLIENT_ID}
