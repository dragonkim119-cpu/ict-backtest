from __future__ import annotations

import numpy as np
import pandas as pd

from app.patterns.config import ATR_PERIOD


def compute_atr(candles: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    """Wilder's ATR.

    TR[0]     = high[0] - low[0]
    TR[i]     = max(high-low, |high-prev_close|, |low-prev_close|)
    ATR[p-1]  = simple mean of first `period` TRs
    ATR[i]    = (ATR[i-1] * (period-1) + TR[i]) / period
    """
    n = len(candles)
    if n == 0:
        return pd.Series([], index=candles.index, dtype="float64")

    high = candles["high"].to_numpy(dtype=float)
    low = candles["low"].to_numpy(dtype=float)
    close = candles["close"].to_numpy(dtype=float)

    tr = np.empty(n, dtype=float)
    tr[0] = high[0] - low[0]
    if n > 1:
        prev_close = close[:-1]
        tr[1:] = np.maximum(
            high[1:] - low[1:],
            np.maximum(np.abs(high[1:] - prev_close), np.abs(low[1:] - prev_close)),
        )

    atr = np.full(n, np.nan, dtype=float)
    if n >= period:
        atr[period - 1] = tr[:period].mean()
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

    return pd.Series(atr, index=candles.index, dtype="float64")
