"""
Phase 11.1: Public API Key Management — generation, validation, usage metering.

Tiers:
  - free:  50 requests/day   (default for new keys)
  - pro:  500 requests/day
  - unlimited: no cap (internal / grant-funded)

Keys are prefixed `vai_` for easy identification.  Usage is tracked per-key
per-day in a lightweight counter table.
"""
import os
import secrets
import logging
from datetime import datetime

from backend.db import get_db, execute_db, ph, USE_POSTGRES

logger = logging.getLogger("fake_news_api")

# ── Tier definitions ──
TIERS = {
    "free":      {"daily_limit": 50,   "label": "Free"},
    "pro":       {"daily_limit": 500,  "label": "Pro"},
    "unlimited": {"daily_limit": None, "label": "Unlimited"},
}
DEFAULT_TIER = "free"


# ── Schema ──

def init_api_keys_db():
    """Create api_keys and api_usage tables if they don't exist."""
    conn = get_db()
    c = conn.cursor()
    ts = "TIMESTAMP" if USE_POSTGRES else "DATETIME"

    if USE_POSTGRES:
        c.execute(f"""CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            key_hash TEXT UNIQUE NOT NULL,
            key_prefix TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT 'Default',
            tier TEXT NOT NULL DEFAULT '{DEFAULT_TIER}',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at {ts} DEFAULT CURRENT_TIMESTAMP,
            last_used_at {ts}
        )""")
        c.execute(f"""CREATE TABLE IF NOT EXISTS api_usage (
            id SERIAL PRIMARY KEY,
            key_id INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
            usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
            request_count INTEGER NOT NULL DEFAULT 0,
            UNIQUE(key_id, usage_date)
        )""")
    else:
        c.execute(f"""CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            key_hash TEXT UNIQUE NOT NULL,
            key_prefix TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT 'Default',
            tier TEXT NOT NULL DEFAULT '{DEFAULT_TIER}',
            active INTEGER NOT NULL DEFAULT 1,
            created_at {ts} DEFAULT CURRENT_TIMESTAMP,
            last_used_at {ts},
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""")
        c.execute(f"""CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_id INTEGER NOT NULL,
            usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
            request_count INTEGER NOT NULL DEFAULT 0,
            UNIQUE(key_id, usage_date),
            FOREIGN KEY(key_id) REFERENCES api_keys(id)
        )""")

    conn.commit()
    conn.close()
    logger.info("api_keys + api_usage tables initialized")


# ── Key Generation ──

def _hash_key(raw_key: str) -> str:
    """Hash an API key for storage using SHA-256."""
    import hashlib
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key(user_id: int, name: str = "Default") -> dict:
    """Create a new API key for a user. Returns the raw key (shown once)."""
    raw_key = f"vai_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:12]  # e.g. "vai_Ab3xK..."

    query = f"""
        INSERT INTO api_keys (user_id, key_hash, key_prefix, name, tier)
        VALUES ({ph(5)})
    """
    execute_db(query, (user_id, key_hash, key_prefix, name, DEFAULT_TIER), commit=True)

    return {
        "key": raw_key,           # Only shown once!
        "prefix": key_prefix,
        "name": name,
        "tier": DEFAULT_TIER,
        "daily_limit": TIERS[DEFAULT_TIER]["daily_limit"],
    }


def list_user_keys(user_id: int) -> list[dict]:
    """List all API keys for a user (without the raw key)."""
    query = f"""
        SELECT id, key_prefix, name, tier, active, created_at, last_used_at
        FROM api_keys WHERE user_id = {ph()}
        ORDER BY created_at DESC
    """
    rows = execute_db(query, (user_id,), fetch="all")
    if not rows:
        return []

    keys = []
    for r in rows:
        tier = r[3]
        keys.append({
            "id": r[0],
            "prefix": r[1],
            "name": r[2],
            "tier": tier,
            "tier_label": TIERS.get(tier, TIERS["free"])["label"],
            "daily_limit": TIERS.get(tier, TIERS["free"])["daily_limit"],
            "active": bool(r[4]),
            "created_at": str(r[5]) if r[5] else None,
            "last_used_at": str(r[6]) if r[6] else None,
        })
    return keys


def revoke_api_key(user_id: int, key_id: int) -> bool:
    """Deactivate an API key. Returns True if the key existed and belonged to the user."""
    query = f"""
        UPDATE api_keys SET active = {('FALSE' if USE_POSTGRES else '0')}
        WHERE id = {ph()} AND user_id = {ph()}
    """
    execute_db(query, (key_id, user_id), commit=True)

    # Check if row was actually found
    check = f"SELECT id FROM api_keys WHERE id = {ph()} AND user_id = {ph()}"
    row = execute_db(check, (key_id, user_id), fetch="one")
    return row is not None


# ── Validation & Usage ──

def validate_api_key(raw_key: str) -> dict | None:
    """Validate an API key. Returns key metadata or None if invalid/inactive.
    
    Also checks daily usage against the tier limit. Returns:
      {"key_id": int, "user_id": int, "tier": str, "daily_limit": int|None,
       "today_usage": int, "allowed": bool}
    or None if the key doesn't exist / is revoked.
    """
    key_hash = _hash_key(raw_key)

    query = f"""
        SELECT id, user_id, tier, active FROM api_keys
        WHERE key_hash = {ph()}
    """
    row = execute_db(query, (key_hash,), fetch="one")
    if not row:
        return None

    key_id, user_id, tier, active = row
    if not active:
        return None

    # Get today's usage
    today = datetime.now().strftime("%Y-%m-%d")
    usage_query = f"""
        SELECT request_count FROM api_usage
        WHERE key_id = {ph()} AND usage_date = {ph()}
    """
    usage_row = execute_db(usage_query, (key_id, today), fetch="one")
    today_usage = usage_row[0] if usage_row else 0

    daily_limit = TIERS.get(tier, TIERS["free"])["daily_limit"]
    allowed = daily_limit is None or today_usage < daily_limit

    return {
        "key_id": key_id,
        "user_id": user_id,
        "tier": tier,
        "daily_limit": daily_limit,
        "today_usage": today_usage,
        "allowed": allowed,
    }


def record_usage(key_id: int) -> None:
    """Increment today's usage counter for a key and update last_used_at."""
    today = datetime.now().strftime("%Y-%m-%d")

    if USE_POSTGRES:
        upsert = """
            INSERT INTO api_usage (key_id, usage_date, request_count)
            VALUES (%s, %s, 1)
            ON CONFLICT (key_id, usage_date)
            DO UPDATE SET request_count = api_usage.request_count + 1
        """
    else:
        upsert = """
            INSERT INTO api_usage (key_id, usage_date, request_count)
            VALUES (?, ?, 1)
            ON CONFLICT (key_id, usage_date)
            DO UPDATE SET request_count = request_count + 1
        """

    execute_db(upsert, (key_id, today), commit=True)

    # Update last_used_at
    ts_func = "NOW()" if USE_POSTGRES else "CURRENT_TIMESTAMP"
    execute_db(
        f"UPDATE api_keys SET last_used_at = {ts_func} WHERE id = {ph()}",
        (key_id,), commit=True
    )


def get_key_usage(key_id: int, days: int = 7) -> list[dict]:
    """Get usage history for a key over the last N days."""
    if USE_POSTGRES:
        query = """
            SELECT usage_date, request_count FROM api_usage
            WHERE key_id = %s AND usage_date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY usage_date DESC
        """
    else:
        query = """
            SELECT usage_date, request_count FROM api_usage
            WHERE key_id = ? AND usage_date >= date('now', '-' || ? || ' days')
            ORDER BY usage_date DESC
        """

    rows = execute_db(query, (key_id, days), fetch="all")
    return [{"date": str(r[0]), "requests": r[1]} for r in (rows or [])]
