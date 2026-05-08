"""Tests for src.core.metrics."""

import pytest
from src.core.metrics import MetricsCollector


class TestMetricsCollector:
    @pytest.fixture
    def m(self):
        return MetricsCollector()

    def test_counter(self, m):
        m.increment("test_counter")
        m.increment("test_counter", 5)
        assert m.get_counter("test_counter") == 6

    def test_histogram(self, m):
        for v in [10, 20, 30, 40, 50]:
            m.observe("test_hist", v)
        snap = m.snapshot()
        h = snap["histograms"]["test_hist"]
        assert h["count"] == 5
        assert h["avg"] == 30.0
        assert h["min"] == 10.0
        assert h["max"] == 50.0

    def test_gauge(self, m):
        m.set_gauge("test_gauge", 42.0)
        snap = m.snapshot()
        assert snap["gauges"]["test_gauge"] == 42.0

    def test_timer(self, m):
        import time
        with m.timer("test_timer"):
            time.sleep(0.01)
        snap = m.snapshot()
        assert snap["histograms"]["test_timer"]["count"] == 1
        assert snap["histograms"]["test_timer"]["avg"] > 0

    def test_snapshot(self, m):
        snap = m.snapshot()
        assert "uptime_seconds" in snap
        assert "counters" in snap
        assert "histograms" in snap
        assert "gauges" in snap

    def test_reset(self, m):
        m.increment("x")
        m.reset()
        assert m.get_counter("x") == 0
