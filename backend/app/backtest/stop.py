from __future__ import annotations

from app.models.patterns import Swing
from app.models.trade import EntrySignal

MAX_SL_DISTANCE_PCT = 0.03
SL_BUFFER_PCT = 0.0005
RISK_REWARD_RATIO = 3.0


def calc_stop_loss(entry: EntrySignal, swings: list[Swing]) -> float | None:
    """Find nearest past swing for SL. Returns None if no valid swing or distance > 3%."""
    if entry.direction == "long":
        valid = [
            s for s in swings
            if s.type == "low"
            and s.index < entry.entry_index
            and s.price < entry.entry_price
        ]
        if not valid:
            return None
        swing = min(valid, key=lambda s: entry.entry_index - s.index)
        sl = swing.price * (1 - SL_BUFFER_PCT)
    else:
        valid = [
            s for s in swings
            if s.type == "high"
            and s.index < entry.entry_index
            and s.price > entry.entry_price
        ]
        if not valid:
            return None
        swing = min(valid, key=lambda s: entry.entry_index - s.index)
        sl = swing.price * (1 + SL_BUFFER_PCT)

    distance = abs(entry.entry_price - sl) / entry.entry_price
    if distance > MAX_SL_DISTANCE_PCT:
        return None
    return sl


def calc_take_profit(entry_price: float, sl: float, direction: str, rr: float = RISK_REWARD_RATIO) -> float:
    if direction == "long":
        risk = entry_price - sl
        return entry_price + risk * rr
    else:
        risk = sl - entry_price
        return entry_price - risk * rr
