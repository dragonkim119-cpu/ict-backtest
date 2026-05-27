from __future__ import annotations

from app.models.trade import Metrics, Trade


def compute_metrics(trades: list[Trade]) -> Metrics:
    if not trades:
        return Metrics(
            total_trades=0, wins=0, losses=0, timeouts=0,
            win_rate=0.0, profit_factor=0.0, expectancy=0.0,
            total_pnl_r=0.0, max_drawdown_r=0.0,
            max_consecutive_losses=0, avg_trade_duration_candles=0.0,
        )

    wins = sum(1 for t in trades if t.status == "closed_win")
    losses = sum(1 for t in trades if t.status == "closed_loss")
    timeouts = sum(1 for t in trades if t.status == "closed_timeout")

    decided = wins + losses
    win_rate = wins / decided if decided > 0 else 0.0

    total_win_r = sum(t.pnl_r for t in trades if t.status == "closed_win")
    total_loss_r = abs(sum(t.pnl_r for t in trades if t.status == "closed_loss"))
    profit_factor = total_win_r / total_loss_r if total_loss_r > 0 else float("inf")

    total_pnl_r = sum(t.pnl_r for t in trades)
    expectancy = total_pnl_r / len(trades)

    max_drawdown_r = _compute_max_drawdown(trades)
    max_consecutive_losses = _compute_max_consecutive_losses(trades)

    durations = [t.exit_index - t.entry.entry_index for t in trades]
    avg_duration = sum(durations) / len(durations)

    return Metrics(
        total_trades=len(trades),
        wins=wins,
        losses=losses,
        timeouts=timeouts,
        win_rate=win_rate,
        profit_factor=profit_factor,
        expectancy=expectancy,
        total_pnl_r=total_pnl_r,
        max_drawdown_r=max_drawdown_r,
        max_consecutive_losses=max_consecutive_losses,
        avg_trade_duration_candles=avg_duration,
    )


def _compute_max_drawdown(trades: list[Trade]) -> float:
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        cumulative += t.pnl_r
        peak = max(peak, cumulative)
        dd = peak - cumulative
        max_dd = max(max_dd, dd)
    return max_dd


def _compute_max_consecutive_losses(trades: list[Trade]) -> int:
    max_streak = 0
    streak = 0
    for t in trades:
        if t.status == "closed_loss":
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak
