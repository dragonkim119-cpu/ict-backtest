from __future__ import annotations

import pandas as pd

from app.models.patterns import BPR
from app.models.trade import EntrySignal


def find_entry_signal(bpr: BPR, candles: pd.DataFrame) -> EntrySignal | None:
    """Return first close-in-BPR signal after BPR creation, or None if invalidated/not found."""
    for i in range(bpr.created_index + 1, len(candles) - 1):
        c = candles.iloc[i]
        if bpr.bottom <= c["close"] <= bpr.top:
            next_candle = candles.iloc[i + 1]
            return EntrySignal(
                bpr=bpr,
                trigger_candle_index=i,
                trigger_candle_time=c["open_time"],
                entry_index=i + 1,
                entry_time=next_candle["open_time"],
                entry_price=next_candle["open"],
                direction="long" if bpr.type == "bull" else "short",
            )
        if bpr.type == "bull" and c["close"] < bpr.bottom:
            return None
        if bpr.type == "bear" and c["close"] > bpr.top:
            return None
    return None
