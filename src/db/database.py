"""
Database module with connection pooling, context manager pattern,
proper error handling, and migration support.

Replaces the old database.py which opened/closed connections on every call.
"""

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from src.core.config import settings
from src.core.exceptions import DatabaseConnectionError, DatabaseError
from src.core.logging_config import get_logger
from src.core.metrics import metrics

logger = get_logger(__name__)

# Schema version — bump when making breaking schema changes
SCHEMA_VERSION = 2

SCHEMA_SQL = """
-- Analysis history
CREATE TABLE IF NOT EXISTS analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_hash TEXT UNIQUE,
    article_text TEXT,
    article_preview TEXT,
    prediction TEXT NOT NULL,
    confidence REAL NOT NULL,
    real_prob REAL,
    fake_prob REAL,
    red_flag_score REAL DEFAULT 0.0,
    ood_score REAL DEFAULT 0.0,
    model_version TEXT,
    model_scores TEXT,
    source_url TEXT,
    source_domain TEXT,
    category TEXT,
    gemini_verdict TEXT,
    web_score REAL,
    final_score REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User feedback
CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_hash TEXT NOT NULL,
    user_rating INTEGER CHECK(user_rating BETWEEN 1 AND 5),
    correct_label TEXT CHECK(correct_label IN ('REAL', 'FAKE', NULL)),
    feedback_text TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_hash) REFERENCES analysis_history(article_hash)
);

-- Source reputation
CREATE TABLE IF NOT EXISTS source_reputation (
    domain TEXT PRIMARY KEY,
    reputation_score REAL DEFAULT 50.0,
    total_analyzed INTEGER DEFAULT 0,
    fake_count INTEGER DEFAULT 0,
    real_count INTEGER DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indices for common queries
CREATE INDEX IF NOT EXISTS idx_history_created ON analysis_history(created_at);
CREATE INDEX IF NOT EXISTS idx_history_prediction ON analysis_history(prediction);
CREATE INDEX IF NOT EXISTS idx_history_hash ON analysis_history(article_hash);
CREATE INDEX IF NOT EXISTS idx_feedback_hash ON user_feedback(article_hash);
"""


class AnalysisDatabase:
    """Thread-safe SQLite database with connection pooling."""

    def __init__(self, db_path: Optional[str] = None):
        raw = db_path or settings.DATABASE_URL
        # Strip 'sqlite:///' prefix if present
        self.db_path = raw.replace("sqlite:///", "")
        self._local = threading.local()
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local connection (connection-per-thread pooling)."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")
                conn.row_factory = sqlite3.Row
                self._local.connection = conn
            except sqlite3.Error as e:
                raise DatabaseConnectionError(f"Cannot connect to database: {e}") from e
        return self._local.connection

    @contextmanager
    def _transaction(self):
        """Context manager for database transactions with automatic rollback."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {e}", exc_info=True)
            raise DatabaseError(f"Database operation failed: {e}") from e

    def _init_schema(self):
        """Initialize or migrate database schema."""
        try:
            with self._transaction() as conn:
                conn.executescript(SCHEMA_SQL)
                # Record schema version
                conn.execute(
                    "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            logger.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise

    @staticmethod
    def _hash_article(text: str) -> str:
        """Generate SHA-256 hash for article deduplication."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]

    def add_analysis(
        self,
        article_text: str,
        prediction: str,
        confidence: float,
        real_prob: float = 0.0,
        fake_prob: float = 0.0,
        red_flag_score: float = 0.0,
        ood_score: float = 0.0,
        model_version: str = "",
        model_scores: Optional[Dict] = None,
        source_url: Optional[str] = None,
        source_domain: Optional[str] = None,
        category: Optional[str] = None,
        gemini_verdict: Optional[str] = None,
        web_score: Optional[float] = None,
        final_score: Optional[float] = None,
    ) -> str:
        """Add an analysis record. Returns the article hash."""
        article_hash = self._hash_article(article_text)
        preview = article_text[:200]

        with self._transaction() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO analysis_history
                   (article_hash, article_text, article_preview, prediction,
                    confidence, real_prob, fake_prob, red_flag_score, ood_score,
                    model_version, model_scores, source_url, source_domain,
                    category, gemini_verdict, web_score, final_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (article_hash, article_text, preview, prediction, confidence,
                 real_prob, fake_prob, red_flag_score, ood_score, model_version,
                 json.dumps(model_scores) if model_scores else None,
                 source_url, source_domain, category, gemini_verdict,
                 web_score, final_score),
            )

        metrics.increment("db_analyses_saved")
        logger.debug(f"Analysis saved: {article_hash[:8]}...")
        return article_hash

    def add_feedback(self, article_hash: str, rating: int,
                     correct_label: Optional[str] = None, feedback_text: Optional[str] = None):
        """Record user feedback for an analysis."""
        with self._transaction() as conn:
            conn.execute(
                """INSERT INTO user_feedback (article_hash, user_rating, correct_label, feedback_text)
                   VALUES (?, ?, ?, ?)""",
                (article_hash, rating, correct_label, feedback_text),
            )
        metrics.increment("db_feedback_received")
        logger.info(f"Feedback recorded: hash={article_hash[:8]}... rating={rating}")

    def get_history(self, limit: int = 100) -> pd.DataFrame:
        """Get recent analysis history as a DataFrame."""
        conn = self._get_connection()
        query = """SELECT id, article_preview, prediction, confidence,
                          real_prob, fake_prob, red_flag_score, model_version,
                          source_domain, category, created_at as timestamp
                   FROM analysis_history ORDER BY created_at DESC LIMIT ?"""
        return pd.read_sql_query(query, conn, params=(limit,))

    def get_statistics(self) -> Dict:
        """Get aggregate statistics."""
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM analysis_history")
        total = cur.fetchone()[0]

        cur.execute("SELECT prediction, COUNT(*) FROM analysis_history GROUP BY prediction")
        pred_counts = dict(cur.fetchall())

        cur.execute("SELECT AVG(confidence) FROM analysis_history")
        avg_conf = cur.fetchone()[0] or 0

        cur.execute("""SELECT article_preview, red_flag_score FROM analysis_history
                       WHERE red_flag_score > 0.5 ORDER BY red_flag_score DESC LIMIT 10""")
        top_flags = cur.fetchall()

        cur.execute("""SELECT category, COUNT(*) FROM analysis_history
                       WHERE category IS NOT NULL GROUP BY category""")
        categories = dict(cur.fetchall())

        return {
            "total": total, "predictions": pred_counts,
            "avg_confidence": avg_conf, "top_red_flags": top_flags,
            "categories": categories,
        }

    def update_source_reputation(self, domain: str, is_fake: bool):
        """Update source reputation based on analysis results."""
        with self._transaction() as conn:
            cur = conn.execute(
                "SELECT total_analyzed, fake_count, real_count FROM source_reputation WHERE domain = ?",
                (domain,),
            )
            row = cur.fetchone()
            if row:
                total, fake, real = row["total_analyzed"] + 1, row["fake_count"], row["real_count"]
                if is_fake: fake += 1
                else: real += 1
            else:
                total, fake, real = 1, (1 if is_fake else 0), (0 if is_fake else 1)

            reputation = (real / total) * 100 if total > 0 else 50
            conn.execute(
                """INSERT OR REPLACE INTO source_reputation
                   (domain, reputation_score, total_analyzed, fake_count, real_count, last_updated)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (domain, reputation, total, fake, real, datetime.now().isoformat()),
            )

    def close(self):
        """Close the thread-local connection."""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
