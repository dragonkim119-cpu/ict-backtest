from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone

import httpx

from app.models.macro import EconomicEvent, NewsItem

logger = logging.getLogger(__name__)

# Simple in-memory cache: key → (fetched_at_unix, data)
_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 300  # 5 min

# Track already-alerted high-impact events to avoid duplicate Telegram sends
_ALERTED: set[str] = set()

# Macro-relevant keywords for Finnhub news filtering
_MACRO_KEYWORDS = [
    "trump", "fed", "federal reserve", "fomc", "tariff", "inflation",
    "recession", "interest rate", "cpi", "nfp", "gdp", "unemployment",
    "geopolit", "sanction", "war", "china", "russia",
]


def _finnhub_token() -> str:
    return os.getenv("FINNHUB_API_KEY", "")


def _cryptopanic_token() -> str:
    return os.getenv("CRYPTOPANIC_API_KEY", "")


def _cache_get(key: str) -> object | None:
    entry = _CACHE.get(key)
    if entry and time.time() - entry[0] < _CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, val: object) -> None:
    _CACHE[key] = (time.time(), val)


async def fetch_economic_calendar(days_ahead: int = 7) -> list[EconomicEvent]:
    cache_key = f"calendar_{days_ahead}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    token = _finnhub_token()
    if not token:
        return []

    today = datetime.now(timezone.utc)
    from_date = today.strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://finnhub.io/api/v1/calendar/economic",
                params={"from": from_date, "to": to_date, "token": token},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("Finnhub calendar fetch failed: %s", exc)
        return []

    events: list[EconomicEvent] = []
    for e in data.get("economicCalendar", []):
        events.append(EconomicEvent(
            event=e.get("event", ""),
            country=e.get("country", ""),
            date=e.get("date", ""),
            time=e.get("time"),
            impact=e.get("impact"),
            actual=e.get("actual"),
            estimate=e.get("estimate"),
            prev=e.get("prev"),
            unit=e.get("unit"),
        ))

    # Keep US events only, sort by date+time
    events = [e for e in events if e.country in ("US", "us", "")]
    events.sort(key=lambda e: (e.date, e.time or ""))

    _cache_set(cache_key, events)
    return events


async def fetch_crypto_news() -> list[NewsItem]:
    cached = _cache_get("crypto_news")
    if cached is not None:
        return cached  # type: ignore[return-value]

    token = _cryptopanic_token()
    items: list[NewsItem] = []

    if not token:
        _cache_set("crypto_news", items)
        return items

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://cryptopanic.com/api/v1/posts/",
                params={
                    "auth_token": token,
                    "currencies": "BTC",
                    "public": "true",
                    "filter": "important",
                },
            )
            if not resp.is_success:
                _cache_set("crypto_news", items)
                return items
            data = resp.json()
    except Exception as exc:
        logger.warning("CryptoPanic fetch failed: %s", exc)
        _cache_set("crypto_news", items)
        return items

    for r in data.get("results", [])[:25]:
        votes = r.get("votes", {}) or {}
        pos = votes.get("positive", 0) or 0
        importance = "high" if pos >= 10 else "medium" if pos >= 3 else "low"
        items.append(NewsItem(
            source="CryptoPanic",
            title=r.get("title", ""),
            url=r.get("url", ""),
            published_at=r.get("published_at", ""),
            currencies=["BTC"],
            importance=importance,
            summary=None,
        ))

    _cache_set("crypto_news", items)
    return items


async def fetch_macro_news() -> list[NewsItem]:
    cached = _cache_get("macro_news")
    if cached is not None:
        return cached  # type: ignore[return-value]

    token = _finnhub_token()
    items: list[NewsItem] = []

    if not token:
        _cache_set("macro_news", items)
        return items

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "general", "token": token},
            )
            if not resp.is_success:
                _cache_set("macro_news", items)
                return items
            data = resp.json()
    except Exception as exc:
        logger.warning("Finnhub news fetch failed: %s", exc)
        _cache_set("macro_news", items)
        return items

    for r in data[:60]:
        headline = (r.get("headline") or "").lower()
        summary = r.get("summary") or ""
        if not any(kw in headline or kw in summary.lower() for kw in _MACRO_KEYWORDS):
            continue
        ts = r.get("datetime", 0)
        published = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else ""
        items.append(NewsItem(
            source=r.get("source", "Finnhub"),
            title=r.get("headline", ""),
            url=r.get("url", ""),
            published_at=published,
            currencies=[],
            importance="medium",
            summary=summary[:200] if summary else None,
        ))
        if len(items) >= 25:
            break

    _cache_set("macro_news", items)
    return items


async def check_and_alert_events(events: list[EconomicEvent]) -> None:
    """Send Telegram alert for high-impact US events within the next 2 hours."""
    from app.services.telegram import is_configured, send_message

    if not is_configured():
        return

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=2)

    for e in events:
        if e.impact != "high":
            continue
        if not e.date or not e.time:
            continue
        alert_key = f"{e.date}_{e.time}_{e.event}"
        if alert_key in _ALERTED:
            continue
        try:
            event_dt = datetime.fromisoformat(f"{e.date}T{e.time}+00:00")
        except ValueError:
            continue
        if now <= event_dt <= cutoff:
            est_str = f"  Est: <b>{e.estimate}{e.unit or ''}</b>" if e.estimate is not None else ""
            prev_str = f"  Prev: {e.prev}{e.unit or ''}" if e.prev is not None else ""
            text = (
                f"📅 <b>High Impact Event</b>\n"
                f"{e.event} ({e.country})\n"
                f"🕐 {e.date} {e.time} UTC{est_str}{prev_str}"
            )
            sent = await send_message(text)
            if sent:
                _ALERTED.add(alert_key)
