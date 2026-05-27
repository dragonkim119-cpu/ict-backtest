from __future__ import annotations

import pandas as pd

from app.models.trade import EntrySignal, Trade


def _unrealized_r(entry: EntrySignal, close: float, sl: float) -> float:
    risk = abs(entry.entry_price - sl)
    if risk == 0:
        return 0.0
    if entry.direction == "long":
        return (close - entry.entry_price) / risk
    else:
        return (entry.entry_price - close) / risk


def simulate_trade(entry: EntrySignal, sl: float, tp: float, candles: pd.DataFrame) -> Trade:
    for i in range(entry.entry_index, len(candles)):
        c = candles.iloc[i]
        if entry.direction == "long":
            hit_sl = c["low"] <= sl
            hit_tp = c["high"] >= tp
        else:
            hit_sl = c["high"] >= sl
            hit_tp = c["low"] <= tp

        if hit_sl and hit_tp:
            return Trade(
                entry=entry, sl=sl, tp=tp,
                exit_index=i, exit_time=c["open_time"],
                exit_price=sl, status="closed_loss", pnl_r=-1.0,
            )
        if hit_sl:
            return Trade(
                entry=entry, sl=sl, tp=tp,
                exit_index=i, exit_time=c["open_time"],
                exit_price=sl, status="closed_loss", pnl_r=-1.0,
            )
        if hit_tp:
            return Trade(
                entry=entry, sl=sl, tp=tp,
                exit_index=i, exit_time=c["open_time"],
                exit_price=tp, status="closed_win", pnl_r=3.0,
            )

    last = candles.iloc[-1]
    return Trade(
        entry=entry, sl=sl, tp=tp,
        exit_index=len(candles) - 1, exit_time=last["open_time"],
        exit_price=last["close"], status="closed_timeout",
        pnl_r=_unrealized_r(entry, last["close"], sl),
    )
