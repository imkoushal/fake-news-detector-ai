"""
Database connection layer — PostgreSQL (production) / SQLite (local dev).
Provides pooled connections, a centralized execution helper, and schema init.
"""
import os
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("fake_news_api")

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = False

if DATABASE_URL:
    try:
        import psycopg2
        USE_POSTGRES = True
    except ImportError:
        pass

if USE_POSTGRES:
    logger.info("PostgreSQL mode — persistent cloud database")
else:
    logger.info("SQLite mode — local development")

# Connection pool for PostgreSQL
_pg_pool = None

if USE_POSTGRES:
    try:
        from psycopg2 import pool as pg_pool
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        # ThreadedConnectionPool is required: FastAPI runs sync DB calls in a
        # threadpool, so getconn/putconn are called concurrently across threads.
        _pg_pool = pg_pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=url)
        logger.info("PostgreSQL connection pool created (1-10 connections, thread-safe)")
    except Exception as e:
        logger.warning(f"Failed to create PostgreSQL connection pool: {e}. Falling back to SQLite.")
        USE_POSTGRES = False
        _pg_pool = None


class _PooledConnection:
    """Wraps a psycopg2 connection so that .close() returns it to the pool."""
    def __init__(self, conn, pool):
        self._conn = conn
        self._pool = pool

    def close(self):
        try:
            self._pool.putconn(self._conn)
        except Exception:
            try:
                self._conn.close()
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_db():
    """Get a database connection (pooled for PostgreSQL).

    For pooled connections, a lightweight ``SELECT 1`` health-check is executed
    before the connection is returned.  Render's free-tier PostgreSQL closes
    idle connections after ~5 min; without this probe the *first* query after
    idle time hits a stale socket and raises ``OperationalError`` (the classic
    "internal error on first try" bug).  On failure the dead connection is
    discarded and a fresh one is obtained from the pool.
    """
    if USE_POSTGRES:
        if _pg_pool:
            conn = _pg_pool.getconn()
            conn.autocommit = False
            # ── Health-check: discard stale connections ──
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                # Clear any implicit transaction opened by the probe so the
                # caller starts with a clean transaction slate.
                conn.rollback()
            except Exception:
                # Connection is dead — throw it away and get a new one.
                logger.warning("Stale PostgreSQL connection detected — discarding and retrying")
                try:
                    _pg_pool.putconn(conn, close=True)
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
                conn = _pg_pool.getconn()
                conn.autocommit = False
            return _PooledConnection(conn, _pg_pool)
        else:
            url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
            import psycopg2
            conn = psycopg2.connect(url)
            conn.autocommit = False
            return conn
    else:
        # check_same_thread=False: connection may be created and used within the
        # same FastAPI threadpool worker; the per-call open/close keeps it safe.
        return sqlite3.connect(str(BASE_DIR / "users.db"), check_same_thread=False)


def ph(n=1):
    """Return SQL placeholder(s) — %s for PostgreSQL, ? for SQLite."""
    p = "%s" if USE_POSTGRES else "?"
    return ", ".join([p] * n)


def execute_db(query: str, params: tuple = (), *, fetch: str = "none", commit: bool = False):
    """Run a SQL query with guaranteed connection cleanup.

    Args:
        query:  SQL string with placeholders.
        params: Tuple of parameter values.
        fetch:  'none' | 'one' | 'all' — what to return from the cursor.
        commit: Whether to commit the transaction.

    Returns:
        None, a single row tuple, or a list of row tuples.
    """
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(query, params)
        if commit:
            conn.commit()
        if fetch == "one":
            return c.fetchone()
        elif fetch == "all":
            return c.fetchall()
        return None
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_auth_db():
    """Create auth/analysis tables if they don't exist, run migrations."""
    conn = get_db()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            google_id TEXT,
            avatar_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS analyses (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            text_preview TEXT NOT NULL,
            prediction TEXT NOT NULL,
            confidence REAL NOT NULL,
            real_prob REAL NOT NULL,
            fake_prob REAL NOT NULL,
            red_flag_score REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            google_id TEXT,
            avatar_url TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text_preview TEXT NOT NULL,
            prediction TEXT NOT NULL,
            confidence REAL NOT NULL,
            real_prob REAL NOT NULL,
            fake_prob REAL NOT NULL,
            red_flag_score REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')

    # On PostgreSQL a failed statement aborts the whole transaction, so every
    # subsequent statement fails with "current transaction is aborted" until a
    # rollback. The migrations below are each expected to fail once the schema
    # has caught up (column already exists), so each one must be isolated —
    # without this, the first no-op migration silently disables all the rest.
    def _migrate(sql: str, success_msg: str):
        try:
            c.execute(sql)
            conn.commit()
            logger.info(success_msg)
        except Exception:
            conn.rollback()  # already applied — clear the aborted transaction

    # Migration: add expires_at column if it doesn't exist
    _migrate(
        "ALTER TABLE sessions ADD COLUMN expires_at " + ("TIMESTAMP" if USE_POSTGRES else "DATETIME"),
        "Migrated sessions table: added expires_at column",
    )

    # Migration: add google_id and avatar_url columns
    for col, col_type in [("google_id", "TEXT"), ("avatar_url", "TEXT DEFAULT ''")]:
        _migrate(
            f"ALTER TABLE users ADD COLUMN {col} {col_type}",
            f"Migrated users table: added {col} column",
        )

    # Migration ledger — lets one-shot data migrations run exactly once instead
    # of on every startup.
    c.execute('''CREATE TABLE IF NOT EXISTS schema_migrations (
        id TEXT PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()

    # One-shot: sessions.token now stores a SHA-256 hash, not the raw token
    # (see backend/auth.py hash_session_token). Rows written before that change
    # hold plaintext tokens. They can no longer authenticate anything — lookups
    # hash the presented value first — but leaving them in place would keep the
    # exact secrets this change exists to remove sitting in the table until
    # their 7-day TTL expires. Drop them; affected users log in again.
    c.execute(f"SELECT 1 FROM schema_migrations WHERE id = {ph()}", ("sessions_token_hashed",))
    if not c.fetchone():
        c.execute("DELETE FROM sessions")
        purged = c.rowcount if c.rowcount and c.rowcount > 0 else 0
        c.execute(
            f"INSERT INTO schema_migrations (id) VALUES ({ph()})",
            ("sessions_token_hashed",),
        )
        conn.commit()
        logger.info(
            f"Migrated sessions table: purged {purged} pre-hash session row(s); "
            "affected users must log in again"
        )

    conn.commit()
    conn.close()

    # Growth metrics table (§5). Imported lazily to avoid a circular import at
    # module load; created here so both app startup and the test harness get it.
    try:
        from backend.metrics import init_metrics_db
        init_metrics_db()
    except Exception as e:
        logger.warning(f"metrics init skipped: {e}")
