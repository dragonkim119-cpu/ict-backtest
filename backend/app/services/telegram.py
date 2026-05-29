from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def _chat_id() -> str:
    return os.getenv("TELEGRAM_CHAT_ID", "")


def get_threshold() -> int:
    return int(os.getenv("TELEGRAM_ALERT_THRESHOLD", "5"))


def is_configured() -> bool:
    return bool(_token()) and bool(_chat_id())


async def send_message(text: str) -> bool:
    """Send a Telegram message. Returns True on success, False if unconfigured or error."""
    token = _token()
    chat_id = _chat_id()
    if not token or not chat_id:
        logger.debug("Telegram not configured, skipping alert")
        return False
    url = _API_URL.format(token=token)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                url,
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("Telegram send failed: %s", exc)
        return False
