from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from app.backtest.entry import find_entry_signal
from app.backtest.metrics import compute_metrics
from app.backtest.simulate import simulate_trade
from app.backtest.stop import calc_stop_loss, calc_take_profit
from app.models.patterns import BPR, Swing
from app.models.trade import EntrySignal, Trade

_BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _ts(hours: int) -> datetime:
    return _BASE + pd.Timedelta(hours=hours)


def _candle(i: int, open_: float, high: float, low: float, close: float) -> dict:
    return {
        "open_time": _ts(i),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1.0,
    }


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _bpr(created_index: int, bottom: float = 99.0, top: float = 101.0, btype: str = "bull") -> BPR:
    return BPR(
        type=btype,
        top=top,
        bottom=bottom,
        fvg_old_time=_ts(0),
        fvg_new_time=_ts(1),
        created_time=_ts(created_index),
        created_index=created_index,
    )


def _swing(index: int, stype: str, price: float) -> Swing:
    return Swing(index=index, type=stype, price=price, time=_ts(index))


def _entry(
    entry_index: int, entry_price: float, direction: str = "long", bpr_obj: BPR | None = None
) -> EntrySignal:
    bpr_obj = bpr_obj or _bpr(0)
    return EntrySignal(
        bpr=bpr_obj,
        trigger_candle_index=entry_index - 1,
        trigger_candle_time=_ts(entry_index - 1),
        entry_index=entry_index,
        entry_time=_ts(entry_index),
        entry_price=entry_price,
        direction=direction,
    )


# ─── Case 1: single Bull BPR → 1 trade, entry price = next candle open ───────

class TestEntrySignal:
    def test_entry_on_next_open(self) -> None:
        bpr = _bpr(created_index=0)
        df = _make_df([
            _candle(0, 100, 102, 98, 100),   # BPR created here (index 0)
            _candle(1, 100, 102, 98, 100),   # trigger: close=100 ∈ [99,101]
            _candle(2, 105, 108, 104, 107),  # entry candle: open=105
        ])
        signal = find_entry_signal(bpr, df)
        assert signal is not None
        assert signal.entry_index == 2
        assert signal.entry_price == 105.0
        assert signal.direction == "long"

    # ─── Case 7: same BPR, only first trigger creates trade ──────────────────

    def test_only_first_trigger(self) -> None:
        """find_entry_signal returns on first match — subsequent closes ignored."""
        bpr = _bpr(created_index=0)
        df = _make_df([
            _candle(0, 100, 102, 98, 100),   # BPR created
            _candle(1, 100, 102, 98, 100),   # first trigger
            _candle(2, 105, 108, 95, 100),   # entry candle; close=100 inside but already returned
            _candle(3, 100, 102, 98, 100),
        ])
        signal = find_entry_signal(bpr, df)
        assert signal is not None
        assert signal.trigger_candle_index == 1

    def test_bull_invalidated_below_bottom(self) -> None:
        bpr = _bpr(created_index=0, bottom=99.0, top=101.0, btype="bull")
        df = _make_df([
            _candle(0, 100, 102, 98, 100),
            _candle(1, 95, 98, 93, 94),   # close < bottom → invalidate
            _candle(2, 100, 102, 98, 100),
        ])
        assert find_entry_signal(bpr, df) is None

    def test_no_signal_when_never_closes_in_bpr(self) -> None:
        bpr = _bpr(created_index=0)
        df = _make_df([
            _candle(0, 100, 102, 98, 100),
            _candle(1, 110, 115, 108, 112),  # above BPR
            _candle(2, 110, 115, 108, 112),
        ])
        assert find_entry_signal(bpr, df) is None


# ─── Case 2: Bull BPR + immediate TP ─────────────────────────────────────────

class TestSimulateTrade:
    def test_win_immediate_tp(self) -> None:
        entry = _entry(entry_index=2, entry_price=105.0)
        sl = 100.0
        tp = 120.0
        df = _make_df([
            _candle(0, 100, 102, 98, 100),
            _candle(1, 100, 102, 98, 100),
            _candle(2, 105, 121, 104, 118),  # high >= tp
        ])
        trade = simulate_trade(entry, sl, tp, df)
        assert trade.status == "closed_win"
        assert trade.pnl_r == pytest.approx(3.0)
        assert trade.exit_price == tp

    # ─── Case 3: Bull BPR + immediate SL ─────────────────────────────────────

    def test_loss_immediate_sl(self) -> None:
        entry = _entry(entry_index=2, entry_price=105.0)
        sl = 100.0
        tp = 120.0
        df = _make_df([
            _candle(0, 100, 102, 98, 100),
            _candle(1, 100, 102, 98, 100),
            _candle(2, 105, 107, 99, 100),  # low <= sl
        ])
        trade = simulate_trade(entry, sl, tp, df)
        assert trade.status == "closed_loss"
        assert trade.pnl_r == pytest.approx(-1.0)
        assert trade.exit_price == sl

    # ─── Case 4: TP and SL on same candle → SL wins (conservative) ───────────

    def test_sl_wins_when_both_hit_same_candle(self) -> None:
        entry = _entry(entry_index=2, entry_price=105.0)
        sl = 100.0
        tp = 120.0
        df = _make_df([
            _candle(0, 100, 102, 98, 100),
            _candle(1, 100, 102, 98, 100),
            _candle(2, 105, 125, 99, 112),  # high >= tp AND low <= sl
        ])
        trade = simulate_trade(entry, sl, tp, df)
        assert trade.status == "closed_loss"
        assert trade.pnl_r == pytest.approx(-1.0)


# ─── Case 5: no swing low → skip entry ───────────────────────────────────────

class TestStopLoss:
    def test_no_swing_low_returns_none_for_long(self) -> None:
        entry = _entry(entry_index=2, entry_price=105.0)
        swings: list[Swing] = []
        assert calc_stop_loss(entry, swings) is None

    # ─── Case 6: SL distance > 3% → skip ─────────────────────────────────────

    def test_sl_too_far_returns_none(self) -> None:
        entry = _entry(entry_index=5, entry_price=100.0)
        swings = [_swing(index=1, stype="low", price=90.0)]  # 10% below entry
        assert calc_stop_loss(entry, swings) is None

    def test_sl_within_limit_returns_price(self) -> None:
        entry = _entry(entry_index=5, entry_price=100.0)
        swings = [_swing(index=1, stype="low", price=98.5)]  # ~1.5% below
        sl = calc_stop_loss(entry, swings)
        assert sl is not None
        assert sl == pytest.approx(98.5 * (1 - 0.0005))

    def test_tp_is_3r_long(self) -> None:
        tp = calc_take_profit(entry_price=100.0, sl=98.0, direction="long")
        # risk = 2.0, tp = 100 + 2*3 = 106
        assert tp == pytest.approx(106.0)

    def test_tp_is_3r_short(self) -> None:
        tp = calc_take_profit(entry_price=100.0, sl=102.0, direction="short")
        # risk = 2.0, tp = 100 - 2*3 = 94
        assert tp == pytest.approx(94.0)


# ─── Metrics ──────────────────────────────────────────────────────────────────

class TestMetrics:
    def _make_trade(
        self, status: str, pnl_r: float, entry_idx: int = 0, exit_idx: int = 5
    ) -> Trade:
        e = _entry(entry_index=entry_idx + 1, entry_price=100.0)
        return Trade(
            entry=e, sl=98.0, tp=106.0,
            exit_index=exit_idx, exit_time=_ts(exit_idx),
            exit_price=98.0 if status == "closed_loss" else 106.0,
            status=status, pnl_r=pnl_r,
        )

    def test_empty_trades(self) -> None:
        m = compute_metrics([])
        assert m.total_trades == 0
        assert m.win_rate == 0.0

    def test_win_rate_excludes_timeouts(self) -> None:
        trades = [
            self._make_trade("closed_win", 3.0),
            self._make_trade("closed_loss", -1.0),
            self._make_trade("closed_timeout", 0.5),
        ]
        m = compute_metrics(trades)
        assert m.wins == 1
        assert m.losses == 1
        assert m.timeouts == 1
        assert m.win_rate == pytest.approx(0.5)

    def test_profit_factor(self) -> None:
        trades = [
            self._make_trade("closed_win", 3.0),
            self._make_trade("closed_win", 3.0),
            self._make_trade("closed_loss", -1.0),
        ]
        m = compute_metrics(trades)
        assert m.profit_factor == pytest.approx(6.0)

    def test_max_drawdown(self) -> None:
        trades = [
            self._make_trade("closed_win", 3.0),
            self._make_trade("closed_loss", -1.0),
            self._make_trade("closed_loss", -1.0),
            self._make_trade("closed_loss", -1.0),
        ]
        m = compute_metrics(trades)
        # peak=3, then 3→2→1→0; max_dd = 3
        assert m.max_drawdown_r == pytest.approx(3.0)

    def test_max_consecutive_losses(self) -> None:
        trades = [
            self._make_trade("closed_loss", -1.0),
            self._make_trade("closed_loss", -1.0),
            self._make_trade("closed_win", 3.0),
            self._make_trade("closed_loss", -1.0),
        ]
        m = compute_metrics(trades)
        assert m.max_consecutive_losses == 2
