"""
Model Monitor — Phase 6.1

Production monitoring system that tracks:
  - Prediction drift (shift in REAL/FAKE ratio over time)
  - Confidence distribution (detecting under-confident or over-confident runs)
  - OOD frequency (how often the model encounters unfamiliar inputs)
  - User feedback accuracy (when users correct predictions)
  - Performance alerts (when metrics degrade beyond thresholds)

Usage:
    from model_monitor import ModelMonitor
    monitor = ModelMonitor()
    monitor.log_prediction(text, prediction, confidence, ood_score, ...)
    report = monitor.get_health_report()
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import numpy as np


class ModelMonitor:
    """Production model health monitor."""

    # Alert thresholds
    THRESHOLDS = {
        "avg_confidence_low": 60.0,      # Alert if avg confidence drops below
        "avg_confidence_high": 97.0,      # Alert if avg confidence suspiciously high
        "ood_rate_high": 0.30,            # Alert if >30% of inputs are OOD
        "fake_rate_high": 0.70,           # Alert if >70% classified as fake
        "fake_rate_low": 0.05,            # Alert if <5% classified as fake
        "feedback_accuracy_low": 0.70,    # Alert if user accuracy feedback <70%
    }

    def __init__(self, db_path: str = "analysis_history.db"):
        self.db_path = db_path
        self._ensure_monitor_tables()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _ensure_monitor_tables(self):
        """Create monitoring tables if they don't exist."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Prediction log table (lightweight, one row per prediction)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prediction_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                prediction TEXT NOT NULL,
                confidence REAL,
                real_prob REAL,
                fake_prob REAL,
                ood_score REAL DEFAULT 0.0,
                ml_weight REAL DEFAULT 0.5,
                gemini_weight REAL DEFAULT 0.3,
                web_weight REAL DEFAULT 0.2,
                red_flag_score REAL DEFAULT 0.0,
                text_length INTEGER,
                category TEXT,
                final_verdict TEXT,
                final_score REAL
            )
        ''')

        # Alert history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitor_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT,
                metric_name TEXT,
                metric_value REAL,
                threshold REAL,
                resolved BOOLEAN DEFAULT 0
            )
        ''')

        # Daily snapshot for trend analysis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_snapshot (
                date TEXT PRIMARY KEY,
                total_predictions INTEGER DEFAULT 0,
                fake_count INTEGER DEFAULT 0,
                real_count INTEGER DEFAULT 0,
                avg_confidence REAL DEFAULT 0,
                avg_ood_score REAL DEFAULT 0,
                ood_count INTEGER DEFAULT 0,
                avg_red_flag REAL DEFAULT 0,
                positive_feedback INTEGER DEFAULT 0,
                negative_feedback INTEGER DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

    def log_prediction(self, prediction: str, confidence: float,
                       real_prob: float = 0.0, fake_prob: float = 0.0,
                       ood_score: float = 0.0, ml_weight: float = 0.5,
                       gemini_weight: float = 0.3, web_weight: float = 0.2,
                       red_flag_score: float = 0.0, text_length: int = 0,
                       category: str = None, final_verdict: str = None,
                       final_score: float = None):
        """Log a single prediction for monitoring."""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO prediction_log
            (timestamp, prediction, confidence, real_prob, fake_prob, ood_score,
             ml_weight, gemini_weight, web_weight, red_flag_score,
             text_length, category, final_verdict, final_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (now, prediction, confidence, real_prob, fake_prob, ood_score,
              ml_weight, gemini_weight, web_weight, red_flag_score,
              text_length, category, final_verdict, final_score))

        conn.commit()
        conn.close()

        # Update daily snapshot
        self._update_daily_snapshot(prediction, confidence, ood_score, red_flag_score)

    def _update_daily_snapshot(self, prediction, confidence, ood_score, red_flag_score):
        """Update today's daily snapshot."""
        conn = self._get_conn()
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")

        # Get existing or create new
        cursor.execute('SELECT * FROM daily_snapshot WHERE date = ?', (today,))
        row = cursor.fetchone()

        if row:
            total = row[1] + 1
            fake = row[2] + (1 if prediction == 'FAKE' else 0)
            real = row[3] + (1 if prediction == 'REAL' else 0)
            # Running average for confidence
            avg_conf = (row[4] * row[1] + confidence) / total
            avg_ood = (row[5] * row[1] + ood_score) / total
            ood_count = row[6] + (1 if ood_score > 0.5 else 0)
            avg_rf = (row[7] * row[1] + red_flag_score) / total

            cursor.execute('''
                UPDATE daily_snapshot SET
                    total_predictions = ?, fake_count = ?, real_count = ?,
                    avg_confidence = ?, avg_ood_score = ?, ood_count = ?,
                    avg_red_flag = ?
                WHERE date = ?
            ''', (total, fake, real, avg_conf, avg_ood, ood_count, avg_rf, today))
        else:
            cursor.execute('''
                INSERT INTO daily_snapshot
                (date, total_predictions, fake_count, real_count,
                 avg_confidence, avg_ood_score, ood_count, avg_red_flag)
                VALUES (?, 1, ?, ?, ?, ?, ?, ?)
            ''', (today,
                  1 if prediction == 'FAKE' else 0,
                  1 if prediction == 'REAL' else 0,
                  confidence, ood_score,
                  1 if ood_score > 0.5 else 0,
                  red_flag_score))

        conn.commit()
        conn.close()

    def get_health_report(self, days: int = 7) -> Dict:
        """Generate comprehensive model health report.
        
        Args:
            days: Number of days to look back.
            
        Returns:
            Dictionary with health metrics and alerts.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # Basic counts
        cursor.execute('''
            SELECT COUNT(*), 
                   AVG(confidence),
                   AVG(ood_score),
                   SUM(CASE WHEN prediction = 'FAKE' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN prediction = 'REAL' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN ood_score > 0.5 THEN 1 ELSE 0 END),
                   AVG(red_flag_score),
                   MIN(confidence),
                   MAX(confidence)
            FROM prediction_log
            WHERE timestamp >= ?
        ''', (cutoff,))

        row = cursor.fetchone()
        total = row[0] or 0

        if total == 0:
            conn.close()
            return {
                "status": "NO_DATA",
                "message": f"No predictions recorded in the last {days} days.",
                "total_predictions": 0,
                "alerts": [],
            }

        avg_conf = row[1] or 0
        avg_ood = row[2] or 0
        fake_count = row[3] or 0
        real_count = row[4] or 0
        ood_count = row[5] or 0
        avg_rf = row[6] or 0
        min_conf = row[7] or 0
        max_conf = row[8] or 0

        fake_rate = fake_count / total if total > 0 else 0
        ood_rate = ood_count / total if total > 0 else 0

        # Confidence distribution buckets
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN confidence < 50 THEN 1 ELSE 0 END),
                SUM(CASE WHEN confidence >= 50 AND confidence < 70 THEN 1 ELSE 0 END),
                SUM(CASE WHEN confidence >= 70 AND confidence < 90 THEN 1 ELSE 0 END),
                SUM(CASE WHEN confidence >= 90 THEN 1 ELSE 0 END)
            FROM prediction_log
            WHERE timestamp >= ?
        ''', (cutoff,))
        conf_dist = cursor.fetchone()

        # Daily trend
        cursor.execute('''
            SELECT date, total_predictions, fake_count, real_count,
                   avg_confidence, avg_ood_score, ood_count
            FROM daily_snapshot
            WHERE date >= ?
            ORDER BY date
        ''', (cutoff[:10],))
        daily_data = cursor.fetchall()

        conn.close()

        # Check for alerts
        alerts = self._check_alerts(
            avg_conf, fake_rate, ood_rate, total, days
        )

        # Overall health status
        critical_alerts = [a for a in alerts if a["severity"] == "critical"]
        warning_alerts = [a for a in alerts if a["severity"] == "warning"]

        if critical_alerts:
            status = "CRITICAL"
        elif warning_alerts:
            status = "WARNING"
        else:
            status = "HEALTHY"

        return {
            "status": status,
            "period_days": days,
            "total_predictions": total,
            "metrics": {
                "avg_confidence": round(avg_conf, 2),
                "min_confidence": round(min_conf, 2),
                "max_confidence": round(max_conf, 2),
                "fake_rate": round(fake_rate, 4),
                "real_rate": round(1 - fake_rate, 4),
                "ood_rate": round(ood_rate, 4),
                "avg_ood_score": round(avg_ood, 4),
                "avg_red_flag_score": round(avg_rf, 4),
                "fake_count": fake_count,
                "real_count": real_count,
                "ood_count": ood_count,
            },
            "confidence_distribution": {
                "low_0_50": conf_dist[0] or 0,
                "medium_50_70": conf_dist[1] or 0,
                "high_70_90": conf_dist[2] or 0,
                "very_high_90_100": conf_dist[3] or 0,
            },
            "daily_trend": [
                {
                    "date": d[0],
                    "total": d[1],
                    "fake": d[2],
                    "real": d[3],
                    "avg_confidence": round(d[4], 2),
                    "avg_ood": round(d[5], 4),
                    "ood_count": d[6],
                }
                for d in daily_data
            ],
            "alerts": alerts,
            "generated_at": datetime.now().isoformat(),
        }

    def _check_alerts(self, avg_conf, fake_rate, ood_rate,
                      total, days) -> List[Dict]:
        """Check metrics against thresholds and generate alerts."""
        alerts = []

        if avg_conf < self.THRESHOLDS["avg_confidence_low"]:
            alerts.append({
                "severity": "warning",
                "type": "low_confidence",
                "message": f"Average confidence ({avg_conf:.1f}%) is below "
                           f"{self.THRESHOLDS['avg_confidence_low']}% threshold.",
                "metric": avg_conf,
                "threshold": self.THRESHOLDS["avg_confidence_low"],
            })

        if avg_conf > self.THRESHOLDS["avg_confidence_high"]:
            alerts.append({
                "severity": "warning",
                "type": "suspicious_high_confidence",
                "message": f"Average confidence ({avg_conf:.1f}%) is suspiciously high "
                           f"(>{self.THRESHOLDS['avg_confidence_high']}%). "
                           f"Check for overfitting or data leakage.",
                "metric": avg_conf,
                "threshold": self.THRESHOLDS["avg_confidence_high"],
            })

        if ood_rate > self.THRESHOLDS["ood_rate_high"]:
            alerts.append({
                "severity": "critical",
                "type": "high_ood_rate",
                "message": f"OOD rate ({ood_rate:.0%}) exceeds "
                           f"{self.THRESHOLDS['ood_rate_high']:.0%} threshold. "
                           f"The model is encountering many unfamiliar inputs. "
                           f"Consider retraining with more diverse data.",
                "metric": ood_rate,
                "threshold": self.THRESHOLDS["ood_rate_high"],
            })

        if fake_rate > self.THRESHOLDS["fake_rate_high"]:
            alerts.append({
                "severity": "critical",
                "type": "high_fake_rate",
                "message": f"Fake detection rate ({fake_rate:.0%}) is very high. "
                           f"Possible model bias or distribution shift.",
                "metric": fake_rate,
                "threshold": self.THRESHOLDS["fake_rate_high"],
            })

        if total > 10 and fake_rate < self.THRESHOLDS["fake_rate_low"]:
            alerts.append({
                "severity": "warning",
                "type": "low_fake_rate",
                "message": f"Fake detection rate ({fake_rate:.0%}) is very low. "
                           f"Model may not be detecting fake news effectively.",
                "metric": fake_rate,
                "threshold": self.THRESHOLDS["fake_rate_low"],
            })

        if not alerts:
            alerts.append({
                "severity": "info",
                "type": "all_clear",
                "message": "All metrics within normal ranges.",
                "metric": None,
                "threshold": None,
            })

        return alerts

    def get_prediction_stats(self, hours: int = 24) -> Dict:
        """Get prediction statistics for the last N hours."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute('''
            SELECT COUNT(*), AVG(confidence), AVG(ood_score),
                   SUM(CASE WHEN prediction = 'FAKE' THEN 1 ELSE 0 END)
            FROM prediction_log
            WHERE timestamp >= ?
        ''', (cutoff,))

        row = cursor.fetchone()
        conn.close()

        total = row[0] or 0
        return {
            "period_hours": hours,
            "total": total,
            "avg_confidence": round(row[1] or 0, 2),
            "avg_ood": round(row[2] or 0, 4),
            "fake_count": row[3] or 0,
            "real_count": total - (row[3] or 0),
        }

    def get_daily_trends(self, days: int = 30) -> List[Dict]:
        """Get daily trend data for charting."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        cursor.execute('''
            SELECT date, total_predictions, fake_count, real_count,
                   avg_confidence, avg_ood_score, ood_count
            FROM daily_snapshot
            WHERE date >= ?
            ORDER BY date
        ''', (cutoff,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "date": r[0],
                "total": r[1],
                "fake": r[2],
                "real": r[3],
                "avg_confidence": round(r[4], 2),
                "avg_ood": round(r[5], 4),
                "ood_count": r[6],
            }
            for r in rows
        ]

    def save_alert(self, alert_type: str, severity: str, message: str,
                   metric_name: str = None, metric_value: float = None,
                   threshold: float = None):
        """Persist an alert to the database."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO monitor_alerts
            (alert_type, severity, message, metric_name, metric_value, threshold)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (alert_type, severity, message, metric_name, metric_value, threshold))
        conn.commit()
        conn.close()

    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        """Get recent alerts."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, alert_type, severity, message,
                   metric_name, metric_value, threshold, resolved
            FROM monitor_alerts
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "timestamp": r[0],
                "type": r[1],
                "severity": r[2],
                "message": r[3],
                "metric_name": r[4],
                "metric_value": r[5],
                "threshold": r[6],
                "resolved": bool(r[7]),
            }
            for r in rows
        ]
