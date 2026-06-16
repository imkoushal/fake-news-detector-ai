"""
API Endpoint Tests — Enterprise E3
Tests all core API endpoints using FastAPI TestClient.
Handles both model-loaded and model-unavailable scenarios gracefully.
"""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

# Check if model is loaded (may fail in CI without lightgbm)
_info = client.get("/api/v1/info").json()
MODEL_LOADED = _info.get("model_loaded", False)


# ── Health & Info ──

class TestHealthEndpoints:
    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ["healthy", "unhealthy"]

    def test_info_endpoint(self):
        r = client.get("/api/v1/info")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data or "model_loaded" in data
        assert "version" in data


# ── Core Analysis ──

class TestAnalyzeEndpoint:
    REAL_ARTICLE = (
        "Washington (Reuters) - The Federal Reserve held interest rates steady on "
        "Wednesday and signaled it would be patient before making any changes. "
        "Fed Chairman Jerome Powell emphasized a data-driven approach at a news "
        "conference after the meeting. The decision was unanimous across all members. "
        "Markets had been closely watching for signals about the central bank's next move. "
        "Economic indicators continue to show mixed signals about the recovery pace."
    )
    FAKE_ARTICLE = (
        "BREAKING!!! DOCTORS DON'T WANT YOU TO KNOW: Ancient herb CURES diabetes "
        "in 3 days! Big Pharma is trying to CENSOR this article! Share before it's "
        "deleted! A revolutionary discovery has sent SHOCKWAVES through the medical "
        "establishment. Mainstream media WON'T report this because pharmaceutical "
        "companies stand to lose BILLIONS! One weird trick that doctors HATE! "
        "Forward this to everyone you know IMMEDIATELY!!!"
    )

    @pytest.mark.skipif(not MODEL_LOADED, reason="ML model not loaded (missing lightgbm)")
    def test_analyze_returns_prediction(self):
        r = client.post("/api/v1/analyze", json={"text": self.REAL_ARTICLE})
        assert r.status_code == 200
        data = r.json()
        assert data["prediction"] in ["REAL", "FAKE"]
        assert 0 <= data["confidence"] <= 100
        assert "real_probability" in data
        assert "fake_probability" in data

    @pytest.mark.skipif(not MODEL_LOADED, reason="ML model not loaded")
    def test_analyze_returns_meta_features(self):
        r = client.post("/api/v1/analyze", json={"text": self.REAL_ARTICLE})
        data = r.json()
        assert "red_flag_score" in data
        assert "input_quality" in data

    @pytest.mark.skipif(not MODEL_LOADED, reason="ML model not loaded")
    def test_analyze_detects_fake_patterns(self):
        r = client.post("/api/v1/analyze", json={"text": self.FAKE_ARTICLE})
        data = r.json()
        assert data["fake_probability"] > 0.3 or data["red_flag_score"] > 0.2

    def test_analyze_rejects_empty_text(self):
        r = client.post("/api/v1/analyze", json={"text": ""})
        # 400 (validation) or 503 (model not loaded) — both acceptable
        assert r.status_code in [400, 422, 503]

    def test_analyze_rejects_too_short(self):
        r = client.post("/api/v1/analyze", json={"text": "hi"})
        assert r.status_code in [400, 422, 503]

    @pytest.mark.skipif(not MODEL_LOADED, reason="ML model not loaded")
    def test_analyze_handles_unicode(self):
        r = client.post("/api/v1/analyze", json={
            "text": "The prime minister announced a new policy to support farmers across the country with additional subsidies."
        })
        assert r.status_code == 200

    @pytest.mark.skipif(not MODEL_LOADED, reason="ML model not loaded")
    def test_analyze_input_quality_short_claim(self):
        r = client.post("/api/v1/analyze", json={"text": "vaccine causes autism share now urgent"})
        data = r.json()
        assert data["input_quality"] in ["short_claim", "headline", "sufficient"]


# ── Fact Check ──

class TestFactCheckEndpoint:
    def test_fact_check_returns_structure(self):
        r = client.post("/api/v1/fact-check", json={"text": "COVID-19 vaccine causes autism"})
        assert r.status_code == 200
        data = r.json()
        assert "available" in data

    def test_fact_check_rejects_empty(self):
        r = client.post("/api/v1/fact-check", json={"text": ""})
        assert r.status_code in [400, 422]


# ── India Threat Scanner ──

class TestIndiaThreatScan:
    def test_detects_upi_scam(self):
        r = client.post("/api/v1/india-threat-scan", json={
            "text": "URGENT: Your SBI account blocked. Share OTP to verify. KYC update required immediately."
        })
        assert r.status_code == 200
        data = r.json()
        assert data["threats_found"] > 0
        assert data["risk_level"] in ["critical", "elevated", "low", "safe"]
        categories = [d["category"] for d in data["detections"]]
        assert "upi_banking_fraud" in categories

    def test_detects_fake_govt_scheme(self):
        r = client.post("/api/v1/india-threat-scan", json={
            "text": "PM Kisan Rs 6000 installment pending. Apply now via registration link. Last date to apply."
        })
        data = r.json()
        assert data["threats_found"] > 0
        categories = [d["category"] for d in data["detections"]]
        assert "fake_govt_scheme" in categories

    def test_detects_whatsapp_forward(self):
        r = client.post("/api/v1/india-threat-scan", json={
            "text": "Forward this to all groups. Please share before they delete it. Must read important message."
        })
        data = r.json()
        assert data["threats_found"] > 0

    def test_clean_article_returns_safe(self):
        r = client.post("/api/v1/india-threat-scan", json={
            "text": "India's GDP grew by 7.2% in Q3, driven by strong manufacturing output and infrastructure spending."
        })
        data = r.json()
        assert data["risk_level"] == "safe"
        assert data["threats_found"] == 0

    def test_rejects_short_text(self):
        r = client.post("/api/v1/india-threat-scan", json={"text": "hi"})
        assert r.status_code == 400


# ── Source Credibility ──

class TestSourceCredibility:
    def test_returns_structure(self):
        r = client.post("/api/v1/source-credibility", json={
            "text": "According to https://www.reuters.com/article/test Reuters reports that the economy is growing."
        })
        assert r.status_code == 200
        data = r.json()
        assert "available" in data

    def test_rejects_empty(self):
        r = client.post("/api/v1/source-credibility", json={"text": ""})
        assert r.status_code in [400, 422]


# ── Cache Stats ──

class TestCacheStats:
    def test_cache_stats_returns_data(self):
        r = client.get("/api/v1/cache-stats")
        assert r.status_code == 200
        data = r.json()
        assert "cache_size" in data
        assert "hits" in data
        assert "misses" in data


# ── Community Stats ──

class TestCommunityStats:
    def test_community_stats_returns_data(self):
        r = client.get("/api/v1/community-stats")
        assert r.status_code == 200
        data = r.json()
        assert "total_analyses" in data
        assert "breakdown" in data


# ── Auth Endpoints ──

class TestAuthEndpoints:
    def test_signup_creates_user(self):
        import random
        email = f"testuser_{random.randint(10000, 99999)}@test.com"
        r = client.post("/api/v1/auth/signup", json={
            "name": "Test User",
            "email": email,
            "password": "SecurePass123!"
        })
        assert r.status_code in [200, 409]

    def test_signup_rejects_short_password(self):
        r = client.post("/api/v1/auth/signup", json={
            "name": "Test", "email": "x@test.com", "password": "123"
        })
        assert r.status_code in [400, 422]

    def test_login_rejects_bad_credentials(self):
        r = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@fake.com", "password": "wrong"
        })
        assert r.status_code == 401

    def test_session_check_rejects_invalid_token(self):
        r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token_xyz"})
        assert r.status_code == 401


# ── Safe Browsing ──

class TestSafeBrowsing:
    def test_safe_browsing_returns_structure(self):
        r = client.post("/api/v1/safe-browsing", json={
            "text": "Check out https://www.google.com for more information"
        })
        assert r.status_code == 200
        data = r.json()
        assert "available" in data


# ── Transcribe (validation only) ──

class TestTranscribe:
    def test_transcribe_rejects_no_file(self):
        r = client.post("/api/v1/transcribe")
        assert r.status_code == 422

    def test_transcribe_rejects_tiny_file(self):
        r = client.post(
            "/api/v1/transcribe",
            files={"audio": ("test.wav", b"tiny", "audio/wav")}
        )
        assert r.status_code == 400
