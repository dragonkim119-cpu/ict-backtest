from __future__ import annotations

import numpy as np
import pandas as pd

from app.models.patterns import Swing
from app.patterns.config import SWING_LOOKBACK


def detect_swings(candles: pd.DataFrame, N: int = SWING_LOOKBACK) -> list[Swing]:
    """Detect swing highs and lows.

    Swing High: candles[i].high is the unique maximum of the 2N+1 window.
    Swing Low:  candles[i].low  is the unique minimum of the 2N+1 window.
    Ties broken by taking the first (leftmost) occurrence.

    Only candles in range [N, len-N) are eligible (need N candles on each side).
    """
    swings: list[Swing] = []
    highs = candles["high"].to_numpy(dtype=float)
    lows = candles["low"].to_numpy(dtype=float)
    n = len(candles)

    for i in range(N, n - N):
        start = i - N
        stop = i + N + 1

        # Swing High: candles[i].high must be the max AND the first occurrence of that max
        window_highs = highs[start:stop]
        if highs[i] == window_highs.max():
            first_max_offset = int(np.argmax(window_highs))
            if start + first_max_offset == i:
                swings.append(
                    Swing(
                        index=i,
                        type="high",
                        price=float(highs[i]),
                        time=candles.iloc[i]["open_time"],
                    )
                )

        # Swing Low: candles[i].low must be the min AND the first occurrence
        window_lows = lows[start:stop]
        if lows[i] == window_lows.min():
            first_min_offset = int(np.argmin(window_lows))
            if start + first_min_offset == i:
                swings.append(
                    Swing(
                        index=i,
                        type="low",
                        price=float(lows[i]),
                        time=candles.iloc[i]["open_time"],
                    )
                )

    return swings
