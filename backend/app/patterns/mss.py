from __future__ import annotations

import pandas as pd

from app.models.patterns import MSSEvent, Swing


def detect_mss(candles: pd.DataFrame, swings: list[Swing]) -> list[MSSEvent]:
    """Detect BOS and CHoCH per docs/02_PATTERNS.md section 10.

    BOS  = break in current trend direction (continuation).
    CHoCH= break against current trend direction (reversal).
    Break criterion: candle close, not wick.
    """
    highs = sorted([s for s in swings if s.type == "high"], key=lambda s: s.index)
    lows  = sorted([s for s in swings if s.type == "low"],  key=lambda s: s.index)

    events: list[MSSEvent] = []
    last_direction: str | None = None
    last_high_broken: Swing | None = None
    last_low_broken:  Swing | None = None

    for i in range(len(candles)):
        c = candles.iloc[i]
        recent_highs = [h for h in highs if h.index < i]
        recent_lows  = [l for l in lows  if l.index < i]
        if not recent_highs or not recent_lows:
            continue

        last_high = recent_highs[-1]
        last_low  = recent_lows[-1]

        if c["close"] > last_high.price and last_high is not last_high_broken:
            etype = "choch" if last_direction == "bear" else "bos"
            events.append(MSSEvent(
                type=etype,
                direction="bull",
                level=last_high.price,
                break_index=i,
                break_time=c["open_time"],
                swing_time=last_high.time,
            ))
            last_high_broken = last_high
            last_direction = "bull"

        elif c["close"] < last_low.price and last_low is not last_low_broken:
            etype = "choch" if last_direction == "bull" else "bos"
            events.append(MSSEvent(
                type=etype,
                direction="bear",
                level=last_low.price,
                break_index=i,
                break_time=c["open_time"],
                swing_time=last_low.time,
            ))
            last_low_broken = last_low
            last_direction = "bear"

    return events
