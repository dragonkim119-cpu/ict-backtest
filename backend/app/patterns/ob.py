from __future__ import annotations

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

    An OB is the last opposing candle immediately before a significant
    displacement (range >= ATR * threshold OR creates an FVG).
    """
    fvg_indices = {f.end_index for f in fvgs}
    obs: list[OrderBlock] = []

    for i in range(lookback + 1, len(candles)):
        c = candles.iloc[i]
        atr_val = float(atr.iloc[i])
        candle_range = c["high"] - c["low"]

        is_displacement = (
            candle_range >= atr_val * displacement_atr_min
            or i in fvg_indices
        )
        if not is_displacement:
            continue

        is_bull_impulse = c["close"] > c["open"]
        is_bear_impulse = c["close"] < c["open"]

        if is_bull_impulse:
            # Find last bearish candle within lookback
            ob_j = None
            for j in range(i - 1, max(i - lookback - 1, -1), -1):
                prev = candles.iloc[j]
                if prev["close"] < prev["open"]:
                    ob_j = j
                    break
            if ob_j is None:
                continue
            oc = candles.iloc[ob_j]
            obs.append(OrderBlock(
                type="bull",
                top=float(oc["open"]),
                bottom=float(oc["close"]),
                ob_index=ob_j,
                ob_time=oc["open_time"],
                created_index=i,
                created_time=c["open_time"],
            ))

        elif is_bear_impulse:
            ob_j = None
            for j in range(i - 1, max(i - lookback - 1, -1), -1):
                prev = candles.iloc[j]
                if prev["close"] > prev["open"]:
                    ob_j = j
                    break
            if ob_j is None:
                continue
            oc = candles.iloc[ob_j]
            obs.append(OrderBlock(
                type="bear",
                top=float(oc["close"]),
                bottom=float(oc["open"]),
                ob_index=ob_j,
                ob_time=oc["open_time"],
                created_index=i,
                created_time=c["open_time"],
            ))

    _update_ob_states(obs, candles)
    return obs


def _update_ob_states(obs: list[OrderBlock], candles: pd.DataFrame) -> None:
    for ob in obs:
        for i in range(ob.created_index + 1, len(candles)):
            c = candles.iloc[i]
            if ob.type == "bull":
                if not ob.mitigated and c["low"] <= ob.top:
                    ob.mitigated = True
                    ob.mitigated_time = c["open_time"]
                if not ob.invalidated and c["close"] < ob.bottom:
                    ob.invalidated = True
                    ob.invalidated_time = c["open_time"]
                    break
            else:
                if not ob.mitigated and c["high"] >= ob.bottom:
                    ob.mitigated = True
                    ob.mitigated_time = c["open_time"]
                if not ob.invalidated and c["close"] > ob.top:
                    ob.invalidated = True
                    ob.invalidated_time = c["open_time"]
                    break
