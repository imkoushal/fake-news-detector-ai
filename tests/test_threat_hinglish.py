"""
Hinglish + Devanagari threat-pattern tests (Phase 10.2).

Exercises scan_india_threats directly (no API/model/network) to confirm the
romanized-Hindi and Devanagari keyword expansion detects the right categories
without introducing false positives on clean English text.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.threat_patterns import scan_india_threats  # noqa: E402


def _categories(text: str) -> list[str]:
    return [d["category"] for d in scan_india_threats(text)["detections"]]


class TestHinglishDetection:
    def test_hinglish_upi_scam(self):
        text = (
            "Aapka SBI khata band ho jayega. Turant KYC update karo aur "
            "verify karne ke liye OTP bhejo, warna account block ho jayega."
        )
        result = scan_india_threats(text)
        assert result["threats_found"] > 0
        assert "upi_banking_fraud" in _categories(text)

    def test_hinglish_fake_job(self):
        text = (
            "Ghar baithe kamaye 50000 rupees har mahine! Sarkari naukri pakki. "
            "Bas registration fees jama karo aur naukri aapki."
        )
        assert "fake_job_scam" in _categories(text)

    def test_hinglish_lottery_reward(self):
        text = "Badhai ho aap jeet gaye! Muft recharge ka inaam claim karo abhi."
        assert "fake_reward_lottery" in _categories(text)


class TestDevanagariDetection:
    def test_devanagari_upi_scam(self):
        text = "आपका खाता बंद हो जाएगा। तुरंत केवाईसी करें और ओटीपी भेजें।"
        result = scan_india_threats(text)
        assert result["threats_found"] > 0
        assert "upi_banking_fraud" in _categories(text)

    def test_devanagari_govt_scheme(self):
        text = "सरकारी योजना के तहत मुफ्त लाभ पाएं। अभी पंजीकरण करें, अंतिम तिथि नजदीक है।"
        assert "fake_govt_scheme" in _categories(text)

    def test_devanagari_health_misinfo(self):
        text = "कोरोना का इलाज इस घरेलू नुस्खा से संभव है। यह रामबाण इलाज है।"
        assert "health_misinfo" in _categories(text)


class TestNoFalsePositives:
    def test_clean_english_article_stays_safe(self):
        # Guards against romanized substrings colliding with English words
        # (e.g. "sena" in "arsenal", "muft" in "mufti").
        text = (
            "India's GDP grew by 7.2% in Q3, driven by strong manufacturing "
            "output, arsenal modernization, and infrastructure spending."
        )
        result = scan_india_threats(text)
        assert result["risk_level"] == "safe"
        assert result["threats_found"] == 0

    def test_clean_hindi_news_stays_low_or_safe(self):
        # Ordinary Hindi news prose should not trip scam categories.
        text = "भारत की अर्थव्यवस्था इस तिमाही में सात प्रतिशत की दर से बढ़ी।"
        result = scan_india_threats(text)
        assert result["risk_level"] in ("safe", "low")
