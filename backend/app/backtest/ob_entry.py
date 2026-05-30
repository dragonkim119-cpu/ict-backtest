from __future__ import annotations

import pandas as pd

from app.models.patterns import OrderBlock
from app.models.trade import EntrySignal

MAX_SL_DISTANCE_PCT = 0.03
SL_BUFFER_PCT = 0.0005


def find_ob_entry_signal(ob: OrderBlock, candles: pd.DataFrame) -> EntrySignal | None:
    """Return first close-in-OB signal after OB creation per docs/03_BACKTEST.md section 8."""
    for i in range(ob.created_index + 1, len(candles) - 1):
        c = candles.iloc[i]
        if ob.bottom <= c["close"] <= ob.top:
            next_candle = candles.iloc[i + 1]
            return EntrySignal(
                ob=ob,
                trigger_candle_index=i,
                trigger_candle_time=c["open_time"],
                entry_index=i + 1,
                entry_time=next_candle["open_time"],
                entry_price=next_candle["open"],
                direction="long" if ob.type == "bull" else "short",
            )
        # Invalidation: close beyond OB body
        if ob.type == "bull" and c["close"] < ob.bottom:
            return None
        if ob.type == "bear" and c["close"] > ob.top:
            return None
    return None


def calc_ob_stop_loss(entry: EntrySignal, ob: OrderBlock) -> float | None:
    """SL = OB body edge + buffer. Returns None if distance > 3%."""
    if entry.direction == "long":
        sl = ob.bottom * (1 - SL_BUFFER_PCT)
    else:
        sl = ob.top * (1 + SL_BUFFER_PCT)

    distance = abs(entry.entry_price - sl) / entry.entry_price
    if distance > MAX_SL_DISTANCE_PCT:
        return None
    return sl
