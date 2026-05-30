from __future__ import annotations

import logging
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx

from app.models.macro import EconomicEvent, NewsItem

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 300  # 5 min

_ALERTED: set[str] = set()

_MACRO_KEYWORDS = [
    "trump", "fed", "federal reserve", "fomc", "tariff", "inflation",
    "recession", "interest rate", "cpi", "nfp", "gdp", "unemployment",
    "geopolit", "sanction", "war", "china", "russia",
]

_RSS_SOURCES = [
    ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
    ("https://cointelegraph.com/rss", "Cointelegraph"),
]


def _finnhub_token() -> str:
    return os.getenv("FINNHUB_API_KEY", "")


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

    events = [e for e in events if e.country in ("US", "us", "")]
    events.sort(key=lambda e: (e.date, e.time or ""))
    _cache_set(cache_key, events)
    return events


async def _fetch_rss(url: str, source: str) -> list[NewsItem]:
    """Parse RSS feed, return NewsItems. No API key required."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "ICT-Backtest/1.0"})
            resp.raise_for_status()
        # Use raw bytes so ET respects the XML encoding declaration (avoids mojibake)
        root = ET.fromstring(resp.content)
    except Exception as exc:
        logger.warning("RSS fetch failed (%s): %s", source, exc)
        return []

    items: list[NewsItem] = []
    for item in root.findall(".//item")[:15]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        pub_raw = item.findtext("pubDate") or ""
        try:
            published = parsedate_to_datetime(pub_raw).isoformat()
        except Exception:
            published = pub_raw
        items.append(NewsItem(
            source=source,
            title=title.strip(),
            url=link.strip(),
            published_at=published,
            currencies=["BTC"],
            importance="medium",
            summary=None,
        ))
    return items


async def fetch_crypto_news() -> list[NewsItem]:
    """Finnhub crypto news + CoinDesk/Cointelegraph RSS. No extra API key needed."""
    cached = _cache_get("crypto_news")
    if cached is not None:
        return cached  # type: ignore[return-value]

    items: list[NewsItem] = []
    token = _finnhub_token()

    # Finnhub crypto category
    if token:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://finnhub.io/api/v1/news",
                    params={"category": "crypto", "token": token},
                )
                if resp.is_success:
                    for r in resp.json()[:20]:
                        ts = r.get("datetime", 0)
                        published = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else ""
                        items.append(NewsItem(
                            source=r.get("source", "Finnhub"),
                            title=r.get("headline", ""),
                            url=r.get("url", ""),
                            published_at=published,
                            currencies=["BTC"],
                            importance="medium",
                            summary=(r.get("summary") or "")[:200] or None,
                        ))
        except Exception as exc:
            logger.warning("Finnhub crypto news failed: %s", exc)

    # RSS feeds (free, no key)
    for rss_url, source in _RSS_SOURCES:
        rss_items = await _fetch_rss(rss_url, source)
        items.extend(rss_items)

    # Dedup by URL, preserve order (first occurrence wins)
    seen_urls: set[str] = set()
    deduped: list[NewsItem] = []
    for item in items:
        if item.url and item.url not in seen_urls:
            seen_urls.add(item.url)
            deduped.append(item)
    deduped.sort(key=lambda n: n.published_at, reverse=True)
    deduped = deduped[:30]
    _cache_set("crypto_news", deduped)
    return deduped


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
        logger.warning("Finnhub macro news failed: %s", exc)
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
