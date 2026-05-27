from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Candle(BaseModel):
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
