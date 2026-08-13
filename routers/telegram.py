"""
Telegram Bot router — webhook handler, voice message transcription, daily quota tracking.
Extracted from api.py as part of P3-3 router split.
"""
import os
import secrets
import logging
import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

import backend.telegram_bot as tg
from backend.threat_patterns import scan_india_threats as _scan_india_threats

logger = logging.getLogger("fake_news_api")

router = APIRouter(tags=["Telegram"])

# Light global daily-call ceiling so a viral spike can't run up external API bills
_tg_budget = {"date": "", "count": 0}
_TG_DAILY_LIMIT = int(os.getenv("TELEGRAM_DAILY_LIMIT", "500"))


def _tg_budget_ok() -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    if _tg_budget["date"] != today:
        _tg_budget["date"] = today
        _tg_budget["count"] = 0
    if _tg_budget["count"] >= _TG_DAILY_LIMIT:
        return False
    _tg_budget["count"] += 1
    return True


async def _tg_handle_check(chat_id: int, text: str):
    """Background task: verify a claim and send the result back to the chat."""
    from api import _run_smart_verify

    try:
        verify = await _run_smart_verify(text, source="telegram")
    except HTTPException as e:
        await tg.send_message(chat_id, f"⚠️ {tg._esc(e.detail)}")
        return
    except Exception as e:
        logger.error(f"Telegram check failed: {e}")
        await tg.send_message(chat_id, "⚠️ Something went wrong while checking. Please try again.")
        return

    threat = None
    try:
        threat = _scan_india_threats(text)
    except Exception as e:
        logger.warning(f"Telegram threat scan failed (non-fatal): {e}")

    await tg.send_message(chat_id, tg.format_verdict_reply(verify, threat))


async def _tg_transcribe_voice(file_id: str) -> str | None:
    """Download a Telegram voice file and transcribe via Groq Whisper."""
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        return None

    audio_bytes = await tg.download_voice(file_id)
    if not audio_bytes:
        return None

    try:
        from backend.http_client import get_client
        resp = await get_client().post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {groq_key}"},
            files={"file": ("voice.ogg", audio_bytes, "audio/ogg")},
            data={"model": "whisper-large-v3", "response_format": "verbose_json", "language": ""},
            timeout=30.0,
        )
        if resp.status_code != 200:
            logger.error(f"Groq Whisper failed for Telegram voice: {resp.status_code}")
            return None
        transcript = resp.json().get("text", "").strip()
        return transcript if transcript else None
    except Exception as e:
        logger.error(f"Telegram voice transcription error: {e}")
        return None


async def _tg_handle_voice(chat_id: int, file_id: str):
    """Background task: transcribe voice → verify → reply."""
    from api import _run_smart_verify

    transcript = await _tg_transcribe_voice(file_id)
    if not transcript:
        await tg.send_message(
            chat_id,
            "⚠️ Couldn't transcribe your voice note. Please try again or send text instead.",
        )
        return

    if len(transcript.strip()) < 10:
        await tg.send_message(
            chat_id,
            f"🎤 <b>Transcript:</b> <i>{tg._esc(transcript)}</i>\n\n"
            "The message is too short to verify — please send a longer voice note.",
        )
        return

    preview = transcript[:200] + ("…" if len(transcript) > 200 else "")
    await tg.send_message(
        chat_id,
        f"🎤 <b>Transcript:</b> <i>{tg._esc(preview)}</i>\n\n🔍 Checking…",
    )

    try:
        verify = await _run_smart_verify(transcript, source="telegram")
    except HTTPException as e:
        await tg.send_message(chat_id, f"⚠️ {tg._esc(e.detail)}")
        return
    except Exception as e:
        logger.error(f"Telegram voice verify failed: {e}")
        await tg.send_message(chat_id, "⚠️ Something went wrong while checking. Please try again.")
        return

    threat = None
    try:
        threat = _scan_india_threats(transcript)
    except Exception:
        pass

    await tg.send_message(chat_id, tg.format_verdict_reply(verify, threat))


# ── Telegram Webhook Endpoint ──

@router.post("/api/v1/telegram/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    """Receive Telegram updates. Validates a shared secret, replies fast, and
    processes the verification in the background."""
    expected = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    _expected_b = expected.encode()
    if (not expected
            or not secrets.compare_digest(secret.encode(), _expected_b)
            or not secrets.compare_digest(header_secret.encode(), _expected_b)):
        logger.warning("Telegram webhook: secret mismatch — ignoring")
        return {"ok": True}

    try:
        update = await request.json()
    except Exception:
        return {"ok": True}

    parsed = tg.parse_update(update)
    if not parsed:
        return {"ok": True}

    chat_id = parsed["chat_id"]
    command = parsed["command"]
    text = parsed["text"]
    voice_file_id = parsed.get("voice_file_id")

    if command in ("/start",):
        await tg.send_message(chat_id, tg.WELCOME_TEXT)
        return {"ok": True}
    if command in ("/help",):
        await tg.send_message(chat_id, tg.HELP_TEXT)
        return {"ok": True}
    if command:
        await tg.send_message(chat_id, tg.HELP_TEXT)
        return {"ok": True}

    if voice_file_id:
        if not tg.allow_request(chat_id):
            await tg.send_message(chat_id, "⏳ You're checking too fast — please wait a moment and try again.")
            return {"ok": True}
        if not _tg_budget_ok():
            await tg.send_message(chat_id, "🛌 VerifAI has hit its free daily check limit. Please try again tomorrow.")
            return {"ok": True}

        await tg.send_message(chat_id, "🎤 Transcribing your voice note… hang on.")
        asyncio.create_task(_tg_handle_voice(chat_id, voice_file_id))
        return {"ok": True}

    if not text or len(text.strip()) < 10:
        await tg.send_message(
            chat_id,
            "Send me a claim, headline, or forwarded message (at least a sentence) and I'll check it. 🎤 You can also send a voice note! /help for tips.",
        )
        return {"ok": True}

    if not tg.allow_request(chat_id):
        await tg.send_message(chat_id, "⏳ You're checking too fast — please wait a moment and try again.")
        return {"ok": True}

    if not _tg_budget_ok():
        await tg.send_message(chat_id, "🛌 VerifAI has hit its free daily check limit. Please try again tomorrow.")
        return {"ok": True}

    await tg.send_message(chat_id, tg.CHECKING_TEXT)
    asyncio.create_task(_tg_handle_check(chat_id, text))
    return {"ok": True}
