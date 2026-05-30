from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.models.macro import MacroCalendarResponse, MacroNewsResponse
from app.services.macro import (
    check_and_alert_events,
    fetch_crypto_news,
    fetch_economic_calendar,
    fetch_macro_news,
)

router = APIRouter()


@router.get("/macro/calendar", response_model=MacroCalendarResponse)
async def get_economic_calendar(
    days: int = Query(7, ge=1, le=30),
    alert: bool = Query(True),
) -> MacroCalendarResponse:
    events = await fetch_economic_calendar(days_ahead=days)
    if alert:
        await check_and_alert_events(events)
    return MacroCalendarResponse(
        events=events,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/macro/news", response_model=MacroNewsResponse)
async def get_macro_news() -> MacroNewsResponse:
    crypto, macro = await fetch_crypto_news(), await fetch_macro_news()
    # Merge and sort by published_at desc
    all_items = crypto + macro
    all_items.sort(key=lambda n: n.published_at, reverse=True)
    return MacroNewsResponse(
        items=all_items[:40],
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/macro/status")
def get_macro_status() -> dict:
    import os
    return {
        "finnhub": bool(os.getenv("FINNHUB_API_KEY")),
        "cryptopanic": bool(os.getenv("CRYPTOPANIC_API_KEY")),
    }
