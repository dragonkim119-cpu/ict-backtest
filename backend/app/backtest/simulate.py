from __future__ import annotations

import pandas as pd

from app.models.trade import EntrySignal, Trade


def _unrealized_r(effective_entry: float, close: float, sl: float, direction: str) -> float:
    risk = abs(effective_entry - sl)
    if risk == 0:
        return 0.0
    if direction == "long":
        return (close - effective_entry) / risk
    else:
        return (effective_entry - close) / risk


def simulate_trade(
    entry: EntrySignal,
    sl: float,
    tp: float,
    candles: pd.DataFrame,
    fee_pct: float = 0.0,
    slippage_pct: float = 0.0,
) -> Trade:
    """Simulate a trade with optional fee and slippage.

    fee_pct      — taker fee fraction per side (e.g. 0.0004 = 0.04%)
    slippage_pct — entry slippage fraction (e.g. 0.0001 = 0.01%)
    """
    # Apply slippage: adverse fill vs. candle open
    if entry.direction == "long":
        effective_entry = entry.entry_price * (1 + slippage_pct)
    else:
        effective_entry = entry.entry_price * (1 - slippage_pct)

    risk = abs(effective_entry - sl)
    # fee in R units: two taker fills (entry + exit) relative to risk
    fee_r = (2 * fee_pct * effective_entry / risk) if risk > 0 else 0.0

    for i in range(entry.entry_index, len(candles)):
        c = candles.iloc[i]
        if entry.direction == "long":
            hit_sl = c["low"] <= sl
            hit_tp = c["high"] >= tp
        else:
            hit_sl = c["high"] >= sl
            hit_tp = c["low"] <= tp

        # SL and TP on same candle → conservative: SL wins
        if hit_sl and hit_tp:
            return Trade(
                entry=entry, sl=sl, tp=tp,
                exit_index=i, exit_time=c["open_time"],
                exit_price=sl, status="closed_loss",
                pnl_r=round(-1.0 - fee_r, 4),
            )
        if hit_sl:
            return Trade(
                entry=entry, sl=sl, tp=tp,
                exit_index=i, exit_time=c["open_time"],
                exit_price=sl, status="closed_loss",
                pnl_r=round(-1.0 - fee_r, 4),
            )
        if hit_tp:
            gross_r = (
                (tp - effective_entry) / risk
                if entry.direction == "long"
                else (effective_entry - tp) / risk
            )
            return Trade(
                entry=entry, sl=sl, tp=tp,
                exit_index=i, exit_time=c["open_time"],
                exit_price=tp, status="closed_win",
                pnl_r=round(gross_r - fee_r, 4),
            )

    last = candles.iloc[-1]
    gross_r = _unrealized_r(effective_entry, last["close"], sl, entry.direction)
    return Trade(
        entry=entry, sl=sl, tp=tp,
        exit_index=len(candles) - 1, exit_time=last["open_time"],
        exit_price=last["close"], status="closed_timeout",
        pnl_r=round(gross_r - fee_r, 4),
    )
