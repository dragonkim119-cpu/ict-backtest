from __future__ import annotations

from typing import Literal

import pandas as pd

from app.models.patterns import PO3
from app.patterns.atr import compute_atr
from app.patterns.config import (
    PO3_ACCUM_ATR_THRESH,
    PO3_ACCUM_LOOKBACK,
    PO3_DISTRIB_ATR_MIN,
    PO3_DISTRIB_WINDOW,
    PO3_MANIP_WINDOW,
)

SESSION_CONFIG: dict[str, tuple[int, int]] = {
    "London": (2, 0),
    "NY_AM": (13, 30),
}


def _session_start_indices(times: pd.Series, start_hour: int, start_min: int) -> list[int]:
    """Positional indices where a new session begins."""
    target = start_hour * 60 + start_min
    result: list[int] = []
    for i in range(1, len(times)):
        t = times.iloc[i]
        pt = times.iloc[i - 1]
        curr = t.hour * 60 + t.minute
        prev = pt.hour * 60 + pt.minute
        same_day = t.date() == pt.date()
        if same_day:
            if prev < target <= curr:
                result.append(i)
        else:
            if curr >= target:
                result.append(i)
    return result


def detect_po3(
    candles: pd.DataFrame,
    atr: pd.Series | None = None,
    session: Literal["London", "NY_AM"] = "NY_AM",
    accum_lookback: int = PO3_ACCUM_LOOKBACK,
    accum_atr_threshold: float | None = PO3_ACCUM_ATR_THRESH,
    manip_window: int = PO3_MANIP_WINDOW,
    distrib_window: int = PO3_DISTRIB_WINDOW,
    distrib_atr_min: float = PO3_DISTRIB_ATR_MIN,
) -> list[PO3]:
    """Detect PO3 cycles for a session.

    accum_atr_threshold=None → AMD mode (no tight-range requirement).
    """
    if len(candles) < accum_lookback + manip_window + 1:
        return []

    if atr is None:
        atr = compute_atr(candles)

    sh, sm = SESSION_CONFIG[session]
    sess_starts = _session_start_indices(candles["open_time"], sh, sm)

    results: list[PO3] = []
    for sess_i in sess_starts:
        if sess_i < accum_lookback:
            continue

        # 1. Accumulation
        accum = candles.iloc[sess_i - accum_lookback : sess_i]
        if len(accum) < 2:
            continue
        accum_high = float(accum["high"].max())
        accum_low = float(accum["low"].min())
        atr_val = float(atr.iloc[sess_i]) if not pd.isna(atr.iloc[sess_i]) else 0.0
        if atr_val == 0.0:
            continue

        if accum_atr_threshold is not None:
            if (accum_high - accum_low) > atr_val * accum_atr_threshold:
                continue

        # 2. Manipulation
        manip_end = min(sess_i + manip_window, len(candles))
        manip_i: int | None = None
        po3_type: Literal["bull", "bear"] | None = None

        for j in range(sess_i, manip_end):
            c = candles.iloc[j]
            if float(c["high"]) > accum_high and float(c["close"]) < accum_high:
                manip_i, po3_type = j, "bear"
                break
            if float(c["low"]) < accum_low and float(c["close"]) > accum_low:
                manip_i, po3_type = j, "bull"
                break

        if manip_i is None or po3_type is None:
            continue

        # 3. Distribution — measure move from manip candle CLOSE (reversal point)
        dist_start = manip_i + 1
        dist_end = min(dist_start + distrib_window, len(candles))
        mc = candles.iloc[manip_i]
        mc_close = float(mc["close"])
        distrib_end_time = None

        for j in range(dist_start, dist_end):
            c = candles.iloc[j]
            if po3_type == "bull":
                move = float(c["high"]) - mc_close
            else:
                move = mc_close - float(c["low"])
            if move >= atr_val * distrib_atr_min:
                distrib_end_time = c["open_time"]
                break

        if distrib_end_time is None:
            continue

        results.append(PO3(
            session=session,
            type=po3_type,
            accum_start_time=accum.iloc[0]["open_time"],
            accum_end_time=accum.iloc[-1]["open_time"],
            accum_high=accum_high,
            accum_low=accum_low,
            manip_time=mc["open_time"],
            manip_extreme=float(mc["low"]) if po3_type == "bull" else float(mc["high"]),
            distrib_start_time=candles.iloc[dist_start]["open_time"],
            distrib_end_time=distrib_end_time,
        ))

    return results
