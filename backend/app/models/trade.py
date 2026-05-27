from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.patterns import BPR


class EntrySignal(BaseModel):
    bpr: BPR
    trigger_candle_index: int
    trigger_candle_time: datetime
    entry_index: int
    entry_time: datetime
    entry_price: float
    direction: Literal["long", "short"]


class Trade(BaseModel):
    entry: EntrySignal
    sl: float
    tp: float
    exit_index: int
    exit_time: datetime
    exit_price: float
    status: Literal["closed_win", "closed_loss", "closed_timeout"]
    pnl_r: float


class Metrics(BaseModel):
    total_trades: int
    wins: int
    losses: int
    timeouts: int
    win_rate: float
    profit_factor: float
    expectancy: float
    total_pnl_r: float
    max_drawdown_r: float
    max_consecutive_losses: int
    avg_trade_duration_candles: float
