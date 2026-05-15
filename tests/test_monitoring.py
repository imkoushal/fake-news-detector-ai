"""
Phase 6 — Model Monitor & Evaluation Tests

Tests for model_monitor.py and eval_report.py.
Run with: pytest tests/test_monitoring.py -v
"""

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── Monitor Tests ───

class TestModelMonitor:
    """Test the ModelMonitor class."""

    @pytest.fixture
    def monitor(self, tmp_path):
        from model_monitor import ModelMonitor
        db_path = str(tmp_path / "test_monitor.db")
        return ModelMonitor(db_path=db_path)

    def test_init_creates_tables(self, monitor):
        """Monitor should create tables on init."""
        import sqlite3
        conn = sqlite3.connect(monitor.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "prediction_log" in tables
        assert "monitor_alerts" in tables
        assert "daily_snapshot" in tables

    def test_log_prediction(self, monitor):
        """Should log a prediction without error."""
        monitor.log_prediction(
            prediction="FAKE",
            confidence=85.0,
            real_prob=0.15,
            fake_prob=0.85,
            ood_score=0.2,
            text_length=500,
        )
        stats = monitor.get_prediction_stats(hours=1)
        assert stats["total"] == 1
        assert stats["fake_count"] == 1

    def test_log_multiple_predictions(self, monitor):
        """Should handle multiple predictions."""
        for i in range(5):
            pred = "REAL" if i % 2 == 0 else "FAKE"
            monitor.log_prediction(prediction=pred, confidence=70.0 + i)
        stats = monitor.get_prediction_stats(hours=1)
        assert stats["total"] == 5
        assert stats["real_count"] == 3
        assert stats["fake_count"] == 2

    def test_health_report_no_data(self, monitor):
        """Health report should handle no data gracefully."""
        report = monitor.get_health_report(days=7)
        assert report["status"] == "NO_DATA"
        assert report["total_predictions"] == 0

    def test_health_report_with_data(self, monitor):
        """Health report should generate metrics."""
        for i in range(10):
            monitor.log_prediction(
                prediction="REAL" if i < 7 else "FAKE",
                confidence=80.0,
                ood_score=0.1,
                red_flag_score=0.1,
            )
        report = monitor.get_health_report(days=1)
        assert report["status"] in ["HEALTHY", "WARNING", "CRITICAL"]
        assert report["total_predictions"] == 10
        assert "metrics" in report
        assert "alerts" in report

    def test_alert_high_ood(self, monitor):
        """Should alert when OOD rate is high."""
        for i in range(10):
            monitor.log_prediction(
                prediction="REAL",
                confidence=60.0,
                ood_score=0.8,  # All OOD
            )
        report = monitor.get_health_report(days=1)
        alert_types = [a["type"] for a in report["alerts"]]
        assert "high_ood_rate" in alert_types

    def test_daily_snapshot_updates(self, monitor):
        """Daily snapshot should track counts correctly."""
        monitor.log_prediction(prediction="REAL", confidence=90.0, ood_score=0.1)
        monitor.log_prediction(prediction="FAKE", confidence=85.0, ood_score=0.6)

        import sqlite3
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(monitor.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_snapshot WHERE date = ?", (today,))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[1] == 2  # total_predictions
        assert row[2] == 1  # fake_count
        assert row[3] == 1  # real_count
        assert row[6] == 1  # ood_count (ood > 0.5)

    def test_save_and_get_alerts(self, monitor):
        """Should persist and retrieve alerts."""
        monitor.save_alert("test_alert", "warning", "Test message",
                          "test_metric", 0.5, 0.3)
        alerts = monitor.get_recent_alerts(limit=5)
        assert len(alerts) == 1
        assert alerts[0]["type"] == "test_alert"
        assert alerts[0]["severity"] == "warning"


# ─── Eval Report Tests ───

class TestEvalReport:
    """Test the evaluation report generator."""

    def test_load_experiments(self):
        from eval_report import load_experiments
        experiments = load_experiments()
        # Should return a list (may be empty if no experiments.csv)
        assert isinstance(experiments, list)

    def test_load_config(self):
        from eval_report import load_config
        config = load_config()
        assert isinstance(config, dict)
        # If config exists, should have accuracy
        if config:
            assert "accuracy" in config

    def test_generate_report(self):
        from eval_report import generate_report
        report = generate_report()
        assert isinstance(report, dict)
        assert "report_type" in report
        assert "model" in report
        assert "performance" in report
        assert "improvement_trajectory" in report

    def test_improvement_trajectory(self):
        from eval_report import compute_improvement_trajectory
        experiments = [
            {"accuracy": "0.92", "f1": "0.91", "roc_auc": "0.98", "model": "v1"},
            {"accuracy": "0.94", "f1": "0.93", "roc_auc": "0.99", "model": "v2"},
        ]
        traj = compute_improvement_trajectory(experiments)
        assert len(traj) == 2
        assert traj[1]["delta_accuracy"] == pytest.approx(0.02, abs=0.001)

    def test_cross_domain_summary(self):
        from eval_report import compute_cross_domain_summary
        cd_data = {
            "matrix": {
                "A→A": {"accuracy": 0.99, "f1": 0.99, "auc": 1.0, "type": "in-domain"},
                "A→B": {"accuracy": 0.80, "f1": 0.78, "auc": 0.90, "type": "cross-domain"},
                "B→A": {"accuracy": 0.70, "f1": 0.68, "auc": 0.85, "type": "cross-domain"},
            },
            "avg_cross_domain_accuracy": 0.75,
            "combined_holdout": {"accuracy": 0.90, "f1": 0.89, "auc": 0.95},
            "dataset_sizes": {"A": 1000, "B": 500},
        }
        summary = compute_cross_domain_summary(cd_data)
        assert summary["in_domain_avg_accuracy"] == pytest.approx(0.99)
        assert summary["n_cross_domain"] == 2
        assert summary["best_cross_domain"]["pair"] == "A→B"
        assert summary["worst_cross_domain"]["pair"] == "B→A"

    def test_report_has_production_health(self):
        from eval_report import generate_report
        report = generate_report()
        assert "production_health" in report
