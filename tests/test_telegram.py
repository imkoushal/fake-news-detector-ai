"""
Telegram bot tests (Phase 9.1).

Covers the pure helpers in backend/telegram_bot.py (formatting, parsing,
throttle) and the webhook endpoint's dispatch logic in api.py. All external IO
(Telegram sends, LLM verification) is mocked, so these run fully offline with no
bot token.
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402
import backend.telegram_bot as tg  # noqa: E402

client = TestClient(api.app)

SECRET = "test-secret-123"

FAKE_VERIFY = {
    "verdict": "LIKELY_FALSE",
    "credibility": "LOW",
    "confidence": 92,
    "analysis": "This is a recurring internet hoax with no credible sourcing.",
    "mode": "rag",
    "web": {
        "available": True,
        "total_articles": 2,
        "trusted_count": 1,
        "articles": [
            {"title": "Fact check: claim is false", "source": "Reuters", "url": "https://reuters.com/x"},
            {"title": "No evidence for claim", "source": "AFP", "url": "https://afp.com/y"},
        ],
    },
}


# ── parse_update ──────────────────────────────────────────────────────────────
class TestParseUpdate:
    def test_extracts_text_message(self):
        p = tg.parse_update({"message": {"chat": {"id": 5}, "text": "hello world"}})
        assert p == {"chat_id": 5, "text": "hello world", "command": None,
                     "voice_file_id": None, "voice_duration": None}

    def test_extracts_voice_message(self):
        p = tg.parse_update({"message": {"chat": {"id": 5},
                             "voice": {"file_id": "abc123", "duration": 10}}})
        assert p["voice_file_id"] == "abc123"
        assert p["voice_duration"] == 10
        assert p["text"] is None

    def test_extracts_command(self):
        p = tg.parse_update({"message": {"chat": {"id": 5}, "text": "/start@VerifAIBot foo"}})
        assert p["command"] == "/start"

    def test_non_text_message_has_none_text(self):
        p = tg.parse_update({"message": {"chat": {"id": 5}, "photo": [{}]}})
        assert p is not None and p["text"] is None

    def test_ignores_updates_without_message(self):
        assert tg.parse_update({"poll": {}}) is None
        assert tg.parse_update({}) is None
        assert tg.parse_update("nonsense") is None


# ── format_verdict_reply ──────────────────────────────────────────────────────
class TestFormatReply:
    def test_fake_verdict_with_evidence(self):
        out = tg.format_verdict_reply(FAKE_VERIFY, None)
        assert "Likely FALSE" in out
        assert "92% confidence" in out
        assert "reuters.com/x" in out  # evidence link
        assert "Verified by VerifAI" in out  # branded footer

    def test_real_verdict(self):
        verify = {**FAKE_VERIFY, "verdict": "LIKELY_TRUE", "confidence": 80}
        out = tg.format_verdict_reply(verify, None)
        assert "Likely TRUE" in out

    def test_no_evidence_note(self):
        verify = {"verdict": "UNVERIFIABLE", "confidence": 40,
                  "analysis": "n/a", "web": {"available": False, "total_articles": 0, "articles": []}}
        out = tg.format_verdict_reply(verify, None)
        assert "style-based" in out.lower()

    def test_threat_flag_shown_when_elevated(self):
        threat = {"risk_level": "critical", "detections": [{"label": "UPI Fraud"}]}
        out = tg.format_verdict_reply(FAKE_VERIFY, threat)
        assert "India scam check" in out
        assert "UPI Fraud" in out

    def test_threat_flag_hidden_when_safe(self):
        threat = {"risk_level": "safe", "detections": []}
        out = tg.format_verdict_reply(FAKE_VERIFY, threat)
        assert "India scam check" not in out

    def test_html_is_escaped(self):
        verify = {"verdict": "MIXED", "confidence": 50,
                  "analysis": "1 < 2 & 3 > 0", "web": {"articles": []}}
        out = tg.format_verdict_reply(verify, None)
        assert "&lt;" in out and "&amp;" in out


# ── throttle ──────────────────────────────────────────────────────────────────
class TestThrottle:
    def test_allows_up_to_limit_then_blocks(self):
        chat = 999001
        assert all(tg.allow_request(chat, limit=3, window=60) for _ in range(3))
        assert tg.allow_request(chat, limit=3, window=60) is False


# ── webhook endpoint ──────────────────────────────────────────────────────────
class TestWebhook:
    def _headers(self):
        return {"X-Telegram-Bot-Api-Secret-Token": SECRET}

    def test_wrong_secret_is_ignored(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
        send = AsyncMock()
        monkeypatch.setattr(tg, "send_message", send)
        r = client.post("/api/v1/telegram/webhook/WRONG",
                        json={"message": {"chat": {"id": 1}, "text": "some claim here"}},
                        headers=self._headers())
        assert r.status_code == 200
        send.assert_not_called()

    def test_start_command_sends_welcome(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
        send = AsyncMock()
        verify = AsyncMock()
        monkeypatch.setattr(tg, "send_message", send)
        monkeypatch.setattr(api, "_run_smart_verify", verify)
        r = client.post(f"/api/v1/telegram/webhook/{SECRET}",
                        json={"message": {"chat": {"id": 1}, "text": "/start"}},
                        headers=self._headers())
        assert r.status_code == 200
        send.assert_awaited_once()
        assert "Welcome to VerifAI" in send.call_args.args[1]
        verify.assert_not_called()  # no verification for a command

    def test_text_triggers_checking_message(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
        send = AsyncMock()
        monkeypatch.setattr(tg, "send_message", send)
        monkeypatch.setattr(api, "_run_smart_verify", AsyncMock(return_value=FAKE_VERIFY))
        r = client.post(f"/api/v1/telegram/webhook/{SECRET}",
                        json={"message": {"chat": {"id": 424242}, "text": "NASA confirms 15 days of darkness in November"}},
                        headers=self._headers())
        assert r.status_code == 200
        # The immediate "Checking…" send is awaited before the background task.
        assert send.await_count >= 1
        assert any(tg.CHECKING_TEXT in c.args[1] for c in send.call_args_list)

    def test_short_text_asks_for_more(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
        send = AsyncMock()
        monkeypatch.setattr(tg, "send_message", send)
        r = client.post(f"/api/v1/telegram/webhook/{SECRET}",
                        json={"message": {"chat": {"id": 1}, "text": "hi"}},
                        headers=self._headers())
        assert r.status_code == 200
        send.assert_awaited_once()
        assert "claim" in send.call_args.args[1].lower()


# ── background handler ────────────────────────────────────────────────────────
class TestHandleCheck:
    def test_sends_formatted_verdict(self, monkeypatch):
        send = AsyncMock()
        monkeypatch.setattr(tg, "send_message", send)
        monkeypatch.setattr(api, "_run_smart_verify", AsyncMock(return_value=FAKE_VERIFY))
        monkeypatch.setattr(api, "_scan_india_threats", lambda t: {"risk_level": "safe", "detections": []})
        asyncio.run(api._tg_handle_check(777, "NASA confirms 15 days of darkness"))
        send.assert_awaited_once()
        body = send.call_args.args[1]
        assert "Likely FALSE" in body and "Verified by VerifAI" in body

    def test_verification_error_sends_friendly_message(self, monkeypatch):
        send = AsyncMock()
        monkeypatch.setattr(tg, "send_message", send)
        monkeypatch.setattr(api, "_run_smart_verify", AsyncMock(side_effect=RuntimeError("boom")))
        asyncio.run(api._tg_handle_check(777, "some claim text here"))
        send.assert_awaited_once()
        assert "went wrong" in send.call_args.args[1].lower()
