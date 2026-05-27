from __future__ import annotations

import numpy as np
import pandas as pd

from app.models.patterns import FVG
from app.patterns.atr import compute_atr
from app.patterns.config import ATR_PERIOD, FVG_ATR_MULTIPLIER


def detect_fvgs(
    candles: pd.DataFrame,
    atr_multiplier: float = FVG_ATR_MULTIPLIER,
    atr_period: int = ATR_PERIOD,
) -> list[FVG]:
    """Detect Bullish and Bearish Fair Value Gaps.

    Bullish FVG: candle[i-2].high < candle[i].low  with gap >= ATR*multiplier
    Bearish FVG: candle[i-2].low  > candle[i].high with gap >= ATR*multiplier
    created_time = candle[i-1].open_time (middle candle).
    """
    atr = compute_atr(candles, period=atr_period).to_numpy(dtype=float)
    high = candles["high"].to_numpy(dtype=float)
    low = candles["low"].to_numpy(dtype=float)
    open_times = candles["open_time"].to_numpy()
    n = len(candles)
    fvgs: list[FVG] = []

    for i in range(2, n):
        min_gap = atr[i] * atr_multiplier
        if np.isnan(min_gap):
            continue

        h_prev = high[i - 2]
        l_prev = low[i - 2]
        l_curr = low[i]
        h_curr = high[i]

        gap_bull = l_curr - h_prev
        if gap_bull > 0 and gap_bull >= min_gap:
            fvgs.append(
                FVG(
                    type="bull",
                    bottom=float(h_prev),
                    top=float(l_curr),
                    start_index=i - 2,
                    middle_index=i - 1,
                    end_index=i,
                    created_time=pd.Timestamp(open_times[i - 1]),
                )
            )
        elif l_prev > h_curr:
            gap_bear = l_prev - h_curr
            if gap_bear >= min_gap:
                fvgs.append(
                    FVG(
                        type="bear",
                        bottom=float(h_curr),
                        top=float(l_prev),
                        start_index=i - 2,
                        middle_index=i - 1,
                        end_index=i,
                        created_time=pd.Timestamp(open_times[i - 1]),
                    )
                )

    return fvgs


def update_fvg_states(fvgs: list[FVG], candles: pd.DataFrame) -> list[FVG]:
    """Update mitigated/invalidated state for each FVG (vectorized).

    Bull FVG:
      Mitigated:   first candle where low  <= fvg.top   (after end_index)
      Invalidated: first candle where close < fvg.bottom (tracking stops)

    Mitigation is only recorded up to and including the invalidation candle.
    Bear FVG: symmetric (high vs bottom, close vs top).
    """
    if not fvgs:
        return fvgs

    low = candles["low"].to_numpy(dtype=float)
    close = candles["close"].to_numpy(dtype=float)
    high = candles["high"].to_numpy(dtype=float)
    open_times = candles["open_time"].to_numpy()
    n = len(candles)

    for fvg in fvgs:
        start = fvg.end_index + 1
        if start >= n:
            continue

        if fvg.type == "bull":
            inv_mask = close[start:] < fvg.bottom
            if inv_mask.any():
                inv_offset = int(inv_mask.argmax())
                fvg.invalidated = True
                fvg.invalidated_time = pd.Timestamp(open_times[start + inv_offset])
                search_end = start + inv_offset + 1  # inclusive of inv candle
            else:
                search_end = n

            mit_mask = low[start:search_end] <= fvg.top
            if mit_mask.any():
                fvg.mitigated = True
                fvg.mitigated_time = pd.Timestamp(open_times[start + int(mit_mask.argmax())])
        else:
            inv_mask = close[start:] > fvg.top
            if inv_mask.any():
                inv_offset = int(inv_mask.argmax())
                fvg.invalidated = True
                fvg.invalidated_time = pd.Timestamp(open_times[start + inv_offset])
                search_end = start + inv_offset + 1
            else:
                search_end = n

            mit_mask = high[start:search_end] >= fvg.bottom
            if mit_mask.any():
                fvg.mitigated = True
                fvg.mitigated_time = pd.Timestamp(open_times[start + int(mit_mask.argmax())])

    return fvgs
