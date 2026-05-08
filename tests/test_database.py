"""Tests for src.db.database."""

import pytest
from src.db.database import AnalysisDatabase


class TestAnalysisDatabase:
    @pytest.fixture
    def db(self, db_path):
        database = AnalysisDatabase(db_path=f"sqlite:///{db_path}")
        yield database
        database.close()

    def test_init_creates_tables(self, db):
        """DB initialization should create all tables without error."""
        stats = db.get_statistics()
        assert stats["total"] == 0

    def test_add_and_retrieve(self, db):
        """Should save and retrieve an analysis."""
        article_hash = db.add_analysis(
            article_text="Test article " * 20,
            prediction="REAL", confidence=95.5,
            real_prob=0.95, fake_prob=0.05,
            red_flag_score=0.1,
        )
        assert article_hash is not None
        assert len(article_hash) == 32

        history = db.get_history(limit=10)
        assert len(history) == 1
        assert history.iloc[0]["prediction"] == "REAL"

    def test_deduplication(self, db):
        """Same article should update, not duplicate."""
        text = "Duplicate article " * 20
        h1 = db.add_analysis(article_text=text, prediction="REAL", confidence=90.0)
        h2 = db.add_analysis(article_text=text, prediction="FAKE", confidence=80.0)
        assert h1 == h2
        assert db.get_statistics()["total"] == 1

    def test_add_feedback(self, db):
        """Should save feedback without error."""
        h = db.add_analysis(article_text="Feedback test " * 20, prediction="FAKE", confidence=80.0)
        db.add_feedback(h, rating=4, correct_label="FAKE")
        # No assertion needed — should not raise

    def test_statistics(self, db):
        """Stats should reflect added data."""
        db.add_analysis(article_text="Real news " * 20, prediction="REAL", confidence=90.0)
        db.add_analysis(article_text="Fake news " * 20, prediction="FAKE", confidence=85.0)

        stats = db.get_statistics()
        assert stats["total"] == 2
        assert stats["predictions"].get("REAL", 0) == 1
        assert stats["predictions"].get("FAKE", 0) == 1

    def test_source_reputation(self, db):
        """Should track source reputation."""
        db.update_source_reputation("example.com", is_fake=False)
        db.update_source_reputation("example.com", is_fake=False)
        db.update_source_reputation("example.com", is_fake=True)
        # No assertion — should not raise

    def test_close(self, db):
        """Close should not raise."""
        db.close()
