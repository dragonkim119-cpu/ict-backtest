from __future__ import annotations

import numpy as np
import pandas as pd

from app.models.patterns import FVG, OrderBlock

OB_DISPLACEMENT_ATR_MIN = 1.5
OB_LOOKBACK = 5
OB_MAX_AGE_CANDLES = 200


def detect_order_blocks(
    candles: pd.DataFrame,
    atr: pd.Series,
    fvgs: list[FVG],
    displacement_atr_min: float = OB_DISPLACEMENT_ATR_MIN,
    lookback: int = OB_LOOKBACK,
) -> list[OrderBlock]:
    """Detect Order Blocks per 02_PATTERNS.md section 9.

    Uses numpy arrays for fast inner-loop access instead of pandas iloc.
    """
    fvg_indices = {f.end_index for f in fvgs}

    # Extract arrays once — avoids repeated pandas iloc overhead
    opens_  = candles["open"].values
    highs_  = candles["high"].values
    lows_   = candles["low"].values
    closes_ = candles["close"].values
    times_  = list(candles["open_time"])   # pd.Timestamp list — Pydantic datetime compatible
    atr_    = atr.values

    obs: list[OrderBlock] = []

    for i in range(lookback + 1, len(candles)):
        atr_val      = float(atr_[i])
        candle_range = highs_[i] - lows_[i]

        is_displacement = (
            candle_range >= atr_val * displacement_atr_min
            or i in fvg_indices
        )
        if not is_displacement:
            continue

        is_bull = closes_[i] > opens_[i]
        is_bear = closes_[i] < opens_[i]

        if is_bull:
            ob_j = None
            for j in range(i - 1, max(i - lookback - 1, -1), -1):
                if closes_[j] < opens_[j]:   # bearish candle
                    ob_j = j
                    break
            if ob_j is None:
                continue
            obs.append(OrderBlock(
                type="bull",
                top=float(opens_[ob_j]),
                bottom=float(closes_[ob_j]),
                ob_index=ob_j,
                ob_time=times_[ob_j],
                created_index=i,
                created_time=times_[i],
            ))

        elif is_bear:
            ob_j = None
            for j in range(i - 1, max(i - lookback - 1, -1), -1):
                if closes_[j] > opens_[j]:   # bullish candle
                    ob_j = j
                    break
            if ob_j is None:
                continue
            obs.append(OrderBlock(
                type="bear",
                top=float(closes_[ob_j]),
                bottom=float(opens_[ob_j]),
                ob_index=ob_j,
                ob_time=times_[ob_j],
                created_index=i,
                created_time=times_[i],
            ))

    # Dedup by (ob_index, type) — keep earliest created_index
    seen: dict[tuple[int, str], OrderBlock] = {}
    for ob in obs:
        key = (ob.ob_index, ob.type)
        if key not in seen or ob.created_index < seen[key].created_index:
            seen[key] = ob
    obs = list(seen.values())
    obs.sort(key=lambda o: o.ob_index)

    _update_ob_states(obs, highs_, lows_, closes_, times_)
    return obs


def _update_ob_states(
    obs: list[OrderBlock],
    highs_: np.ndarray,
    lows_: np.ndarray,
    closes_: np.ndarray,
    times_: list,
) -> None:
    n = len(closes_)
    for ob in obs:
        for i in range(ob.created_index + 1, n):
            if ob.type == "bull":
                if not ob.mitigated and lows_[i] <= ob.top:
                    ob.mitigated = True
                    ob.mitigated_time = times_[i]
                if not ob.invalidated and closes_[i] < ob.bottom:
                    ob.invalidated = True
                    ob.invalidated_time = times_[i]
                    break
            else:
                if not ob.mitigated and highs_[i] >= ob.bottom:
                    ob.mitigated = True
                    ob.mitigated_time = times_[i]
                if not ob.invalidated and closes_[i] > ob.top:
                    ob.invalidated = True
                    ob.invalidated_time = times_[i]
                    break
