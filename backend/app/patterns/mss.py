from __future__ import annotations

import pandas as pd

from app.models.patterns import MSSEvent, Swing


def detect_mss(candles: pd.DataFrame, swings: list[Swing]) -> list[MSSEvent]:
    """Detect BOS and CHoCH — O(n) using sorted-pointer approach.

    Previous implementation did O(n * swings) list-comprehension per candle.
    Now we advance two pointers (hi, li) through pre-sorted swing lists,
    reducing to O(n + swings).
    """
    highs = sorted([s for s in swings if s.type == "high"], key=lambda s: s.index)
    lows  = sorted([s for s in swings if s.type == "low"],  key=lambda s: s.index)

    if not highs or not lows:
        return []

    events: list[MSSEvent] = []
    last_direction: str | None = None
    last_high_broken: Swing | None = None
    last_low_broken:  Swing | None = None

    # Pointers: highs[:hi] are all swings with index < current candle i
    hi = 0
    li = 0
    closes = candles["close"].values
    times  = candles["open_time"].values

    for i in range(len(candles)):
        # Advance pointers to include only swings confirmed before candle i
        while hi < len(highs) and highs[hi].index < i:
            hi += 1
        while li < len(lows) and lows[li].index < i:
            li += 1

        if hi == 0 or li == 0:
            continue

        last_high = highs[hi - 1]
        last_low  = lows[li - 1]
        close_i   = float(closes[i])
        time_i    = times[i]

        if close_i > last_high.price and last_high is not last_high_broken:
            etype = "choch" if last_direction == "bear" else "bos"
            events.append(MSSEvent(
                type=etype,
                direction="bull",
                level=last_high.price,
                break_index=i,
                break_time=time_i,
                swing_time=last_high.time,
            ))
            last_high_broken = last_high
            last_direction = "bull"

        elif close_i < last_low.price and last_low is not last_low_broken:
            etype = "choch" if last_direction == "bull" else "bos"
            events.append(MSSEvent(
                type=etype,
                direction="bear",
                level=last_low.price,
                break_index=i,
                break_time=time_i,
                swing_time=last_low.time,
            ))
            last_low_broken = last_low
            last_direction = "bear"

    return events
