from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class JournalEntryCreate(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str
    direction: Literal["long", "short"]
    entry_time: datetime
    exit_time: datetime | None = None
    entry_price: float
    exit_price: float | None = None
    sl: float | None = None
    tp: float | None = None
    result_pnl: float | None = None
    rr: float | None = None
    notes: str = ""
    tags: list[str] = []
    run_id: str | None = None


class JournalEntryUpdate(BaseModel):
    exit_time: datetime | None = None
    exit_price: float | None = None
    sl: float | None = None
    tp: float | None = None
    result_pnl: float | None = None
    rr: float | None = None
    notes: str | None = None
    tags: list[str] | None = None
    run_id: str | None = None


class JournalEntry(JournalEntryCreate):
    id: int
    created_at: datetime


class JournalCompareResult(BaseModel):
    journal: JournalEntry
    run: dict | None = None
    trades: list[dict] | None = None


# ── stats models ───────────────────────────────────────────────────


class WeekdayStat(BaseModel):
    day: str
    total: int
    wins: int
    win_rate: float


class HourStat(BaseModel):
    hour: int
    total: int
    wins: int
    win_rate: float


class MonthStat(BaseModel):
    month: str
    total: int
    wins: int
    pnl_r: float


class DirectionStat(BaseModel):
    direction: str
    total: int
    wins: int
    win_rate: float
    avg_pnl_r: float | None


class IntervalStat(BaseModel):
    interval: str
    total: int
    wins: int
    win_rate: float


class JournalStats(BaseModel):
    closed_total: int
    wins: int
    losses: int
    win_rate: float
    avg_rr: float | None
    total_pnl_r: float
    by_weekday: list[WeekdayStat]
    by_hour: list[HourStat]
    by_month: list[MonthStat]
    by_direction: list[DirectionStat]
    by_interval: list[IntervalStat]


class BacktestAggregate(BaseModel):
    total_runs: int
    avg_win_rate: float | None
    avg_profit_factor: float | None
    avg_total_pnl_r: float | None


class JournalVsBacktest(BaseModel):
    journal: JournalStats
    backtest: BacktestAggregate
