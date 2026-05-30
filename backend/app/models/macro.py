from __future__ import annotations

from pydantic import BaseModel


class EconomicEvent(BaseModel):
    event: str
    country: str
    date: str
    time: str | None = None
    impact: str | None = None  # "high" | "medium" | "low"
    actual: float | None = None
    estimate: float | None = None
    prev: float | None = None
    unit: str | None = None


class NewsItem(BaseModel):
    source: str
    title: str
    url: str
    published_at: str
    currencies: list[str] = []
    importance: str | None = None  # "high" | "medium" | "low"
    summary: str | None = None


class MacroCalendarResponse(BaseModel):
    events: list[EconomicEvent]
    fetched_at: str


class MacroNewsResponse(BaseModel):
    items: list[NewsItem]
    fetched_at: str
