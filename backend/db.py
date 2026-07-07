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
    """Get a database connection (pooled for PostgreSQL)."""
    if USE_POSTGRES:
        if _pg_pool:
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

    # Migration: add expires_at column if it doesn't exist
    try:
        if USE_POSTGRES:
            c.execute("ALTER TABLE sessions ADD COLUMN expires_at TIMESTAMP")
        else:
            c.execute("ALTER TABLE sessions ADD COLUMN expires_at DATETIME")
        logger.info("Migrated sessions table: added expires_at column")
    except Exception:
        pass  # Column already exists

    # Migration: add google_id and avatar_url columns
    for col, col_type in [("google_id", "TEXT"), ("avatar_url", "TEXT DEFAULT ''")]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
            logger.info(f"Migrated users table: added {col} column")
        except Exception:
            pass  # Column already exists

    conn.commit()
    conn.close()

    # Growth metrics table (§5). Imported lazily to avoid a circular import at
    # module load; created here so both app startup and the test harness get it.
    try:
        from backend.metrics import init_metrics_db
        init_metrics_db()
    except Exception as e:
        logger.warning(f"metrics init skipped: {e}")
