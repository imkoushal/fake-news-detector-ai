"""
VerifAI Telegram bot — thin adapter over the existing verification engine.

This module holds *pure* helpers with no dependency on api.py (avoids a circular
import): outbound Telegram IO, update parsing, reply formatting, and a small
per-chat throttle. The orchestration (calling the verification core + threat
scan, then sending the reply) lives in the webhook handler in api.py.

Env vars:
  TELEGRAM_BOT_TOKEN       — from @BotFather
  TELEGRAM_WEBHOOK_SECRET  — random string; part of the webhook URL + header
"""
from __future__ import annotations

import html
import logging
import os
import time
from collections import defaultdict
from threading import Lock

logger = logging.getLogger("fake_news_api")

BOT_API_BASE = "https://api.telegram.org/bot{token}"

# Branding — every reply carries attribution (growth loop + license ethos).
SITE_URL = "https://fake-news-detector-8djq.onrender.com"
FOOTER = f'🔍 <b>Verified by VerifAI</b> — <a href="{SITE_URL}">verifai</a>'

WELCOME_TEXT = (
    "👋 <b>Welcome to VerifAI</b> — your misinformation checker.\n\n"
    "Forward me any news, message, or link and I'll tell you whether it looks "
    "<b>real</b> or <b>fake</b>, with live evidence and an India-scam check.\n\n"
    "Just send text to get started, or /help for tips."
)

HELP_TEXT = (
    "<b>How to use VerifAI</b>\n\n"
    "• Paste or forward any claim, headline, or WhatsApp forward.\n"
    "• I cross-check it against live news and known Indian scam patterns.\n"
    "• You'll get a verdict, a confidence score, and sources.\n\n"
    "<i>Tip:</i> the more complete the claim, the better the check.\n\n"
    + FOOTER
)

CHECKING_TEXT = "🔍 Checking… hang on a few seconds."

# Verdict → (emoji, human label). Keys match _call_groq's verdict values.
_VERDICT_DISPLAY = {
    "LIKELY_TRUE": ("✅", "Likely TRUE"),
    "LIKELY_FALSE": ("❌", "Likely FALSE"),
    "MIXED": ("⚠️", "MIXED / partly true"),
    "UNVERIFIABLE": ("🔍", "Unverified"),
}

_MAX_ANALYSIS_CHARS = 500
_MAX_EVIDENCE_LINKS = 2


# ── Per-chat throttle ────────────────────────────────────────────────────────
_throttle_lock = Lock()
_throttle_hits: dict[int, list[float]] = defaultdict(list)


def allow_request(chat_id: int, limit: int = 5, window: float = 60.0) -> bool:
    """Sliding-window throttle: allow `limit` checks per `window` seconds per chat.

    Webhook traffic all originates from Telegram's IPs, so SlowAPI's per-IP limit
    is useless here — we throttle per Telegram chat instead.
    """
    now = time.monotonic()
    with _throttle_lock:
        hits = _throttle_hits[chat_id]
        # Drop timestamps outside the window
        hits[:] = [t for t in hits if now - t < window]
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


# ── Update parsing ───────────────────────────────────────────────────────────
def parse_update(update: dict) -> dict | None:
    """Extract the bits we care about from a Telegram update.

    Returns a dict {chat_id, text, command} or None if there's no usable message.
    - text is None when the message has no text (photo/sticker/etc.).
    - command is the lowercased command (e.g. "/start") or None.
    """
    if not isinstance(update, dict):
        return None
    msg = update.get("message") or update.get("edited_message") or update.get("channel_post")
    if not isinstance(msg, dict):
        return None
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return None

    text = msg.get("text")
    command = None
    if isinstance(text, str) and text.startswith("/"):
        # "/start@BotName arg" → "/start"
        command = text.split()[0].split("@")[0].lower()

    return {"chat_id": chat_id, "text": text, "command": command}


# ── Reply formatting ─────────────────────────────────────────────────────────
def _esc(s: str) -> str:
    """Escape text for Telegram HTML parse mode."""
    return html.escape(str(s or ""), quote=False)


def format_verdict_reply(verify: dict, threat: dict | None = None) -> str:
    """Build the branded HTML verdict reply from a _run_smart_verify result
    and an optional scan_india_threats result."""
    verify = verify or {}
    verdict = str(verify.get("verdict", "UNVERIFIABLE")).upper()
    emoji, label = _VERDICT_DISPLAY.get(verdict, _VERDICT_DISPLAY["UNVERIFIABLE"])
    confidence = verify.get("confidence")

    lines = []
    header = f"{emoji} <b>{_esc(label)}</b>"
    if isinstance(confidence, (int, float)):
        header += f"  ({int(confidence)}% confidence)"
    lines.append(header)

    analysis = str(verify.get("analysis", "")).strip()
    if analysis:
        if len(analysis) > _MAX_ANALYSIS_CHARS:
            analysis = analysis[:_MAX_ANALYSIS_CHARS].rstrip() + "…"
        lines.append("")
        lines.append(_esc(analysis))

    # Evidence links
    web = verify.get("web") or {}
    articles = web.get("articles") or []
    shown = [a for a in articles if a.get("url") and a.get("title")][:_MAX_EVIDENCE_LINKS]
    if shown:
        lines.append("")
        lines.append("<b>Evidence:</b>")
        for a in shown:
            src = _esc(a.get("source", "source"))
            title = _esc(a.get("title", ""))
            url = _esc(a.get("url", ""))
            lines.append(f'• <a href="{url}">{title}</a> — {src}')
    elif web.get("available") is False or web.get("total_articles") == 0:
        lines.append("")
        lines.append("<i>No live news coverage found — verdict is style-based only.</i>")

    # India scam / threat flag (only surface elevated+ risk to avoid noise)
    if threat and threat.get("risk_level") in ("elevated", "critical"):
        dets = threat.get("detections") or []
        labels = ", ".join(_esc(d.get("label", "")) for d in dets[:3] if d.get("label"))
        lines.append("")
        risk = _esc(str(threat.get("risk_level", "")).upper())
        flag = "🚨" if threat.get("risk_level") == "critical" else "🟡"
        lines.append(f"{flag} <b>India scam check:</b> {risk} RISK")
        if labels:
            lines.append(f"Matches: {labels}")

    lines.append("")
    lines.append(FOOTER)
    return "\n".join(lines)


# ── Outbound Telegram IO ─────────────────────────────────────────────────────
def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


async def send_message(chat_id: int, text: str, disable_preview: bool = True) -> bool:
    """Send an HTML message to a chat. Returns True on success.

    Uses the shared httpx client. Never raises — logs and returns False so a
    failed send can't crash the background task.
    """
    token = _token()
    if not token:
        logger.warning("Telegram send skipped: TELEGRAM_BOT_TOKEN not set")
        return False
    try:
        from backend.http_client import get_client
        resp = await get_client().post(
            BOT_API_BASE.format(token=token) + "/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": disable_preview,
            },
        )
        if resp.status_code != 200:
            logger.error(f"Telegram sendMessage failed {resp.status_code}: {resp.text[:200]}")
            return False
        return True
    except Exception as e:  # noqa: BLE001 — never let a send crash the caller
        logger.error(f"Telegram sendMessage error: {e}")
        return False


async def set_webhook(base_url: str, secret: str) -> bool:
    """Register the webhook with Telegram (idempotent). Called once on startup.

    `base_url` is the public https origin (no trailing slash). The secret is
    embedded in the path AND sent as secret_token so Telegram echoes it back in
    the X-Telegram-Bot-Api-Secret-Token header.
    """
    token = _token()
    if not token or not base_url or not secret:
        return False
    webhook_url = f"{base_url.rstrip('/')}/api/v1/telegram/webhook/{secret}"
    try:
        from backend.http_client import get_client
        resp = await get_client().post(
            BOT_API_BASE.format(token=token) + "/setWebhook",
            json={
                "url": webhook_url,
                "secret_token": secret,
                "allowed_updates": ["message", "edited_message"],
            },
        )
        ok = resp.status_code == 200 and resp.json().get("ok") is True
        if ok:
            logger.info(f"Telegram webhook registered → {webhook_url}")
        else:
            logger.error(f"Telegram setWebhook failed {resp.status_code}: {resp.text[:200]}")
        return ok
    except Exception as e:  # noqa: BLE001
        logger.error(f"Telegram setWebhook error: {e}")
        return False
