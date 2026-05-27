"""Week 3: Liquidity Pool + Sweep 단위 테스트."""

from __future__ import annotations

import pandas as pd
import pytest

from app.models.patterns import Swing
from app.patterns.liquidity import _Pool, detect_liquidity_pools, detect_sweeps


def _swing(idx: int, stype: str, price: float) -> Swing:
    return Swing(
        index=idx,
        type=stype,  # type: ignore[arg-type]
        price=price,
        time=pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=idx),
    )


def _candle_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    return df.reset_index(drop=True)


class TestDetectLiquidityPools:
    def test_equal_highs_form_bsl(self) -> None:
        """3 swing highs within tolerance → 1 BSL pool."""
        swings = [
            _swing(10, "high", 100.0),
            _swing(20, "high", 100.05),  # 0.05% diff < 0.1% tolerance
            _swing(30, "high", 99.96),  # 0.04% diff
        ]
        pools = detect_liquidity_pools(swings)
        bsl = [p for p in pools if p.side == "BSL"]
        assert len(bsl) == 1
        assert bsl[0].level == pytest.approx((100.0 + 100.05 + 99.96) / 3, rel=1e-6)

    def test_equal_lows_form_ssl(self) -> None:
        """3 swing lows within tolerance → 1 SSL pool."""
        swings = [
            _swing(10, "low", 50.0),
            _swing(20, "low", 50.04),
            _swing(30, "low", 49.97),
        ]
        pools = detect_liquidity_pools(swings)
        ssl = [p for p in pools if p.side == "SSL"]
        assert len(ssl) == 1

    def test_far_apart_highs_no_pool(self) -> None:
        """Swing highs > 0.1% apart → 0 BSL pools."""
        swings = [
            _swing(10, "high", 100.0),
            _swing(20, "high", 102.0),  # 2% apart → new cluster, only 1 swing each
        ]
        pools = detect_liquidity_pools(swings)
        bsl = [p for p in pools if p.side == "BSL"]
        assert len(bsl) == 0

    def test_min_count_2_required(self) -> None:
        """Single swing cannot form a pool (min_count=2)."""
        swings = [_swing(10, "high", 100.0)]
        pools = detect_liquidity_pools(swings, min_count=2)
        assert len(pools) == 0

    def test_two_clusters_form_two_pools(self) -> None:
        """Swing highs in two distinct price clusters → 2 BSL pools."""
        swings = [
            _swing(10, "high", 100.0),
            _swing(20, "high", 100.05),  # cluster A
            _swing(30, "high", 200.0),
            _swing(40, "high", 200.08),  # cluster B (0.04% diff)
        ]
        pools = detect_liquidity_pools(swings)
        bsl = [p for p in pools if p.side == "BSL"]
        assert len(bsl) == 2

    def test_no_swings_no_pools(self) -> None:
        """Empty swings list → empty pools."""
        assert detect_liquidity_pools([]) == []

    def test_pool_level_is_average(self) -> None:
        """Pool level equals mean of cluster prices."""
        swings = [_swing(i, "high", 100.0 + i * 0.01) for i in range(3)]
        pools = detect_liquidity_pools(swings)
        bsl = [p for p in pools if p.side == "BSL"]
        assert len(bsl) == 1
        expected_level = (100.0 + 100.01 + 100.02) / 3
        assert bsl[0].level == pytest.approx(expected_level, rel=1e-6)


class TestDetectSweeps:
    def _make_pool(self, side: str, level: float, last_idx: int = -1) -> _Pool:
        """last_idx: pool's last_swing_index; sweep detection starts at last_idx + 1."""
        stype = "high" if side == "BSL" else "low"
        return _Pool(  # type: ignore[arg-type]
            side=side,
            level=level,
            swings=[_swing(last_idx - 1, stype, level), _swing(last_idx, stype, level)],
        )

    def test_bsl_sweep_detected(self) -> None:
        """BSL swept: candle.high > level AND candle.close < level."""
        pool = self._make_pool("BSL", 100.0)
        df = _candle_df(
            [
                {
                    "open_time": "2024-01-01T10:00:00Z",
                    "open": 95.0,
                    "high": 99.0,
                    "low": 94.0,
                    "close": 96.0,
                    "volume": 1000.0,
                },
                # i=1: wick above 100, closes below → sweep
                {
                    "open_time": "2024-01-01T11:00:00Z",
                    "open": 98.0,
                    "high": 102.0,
                    "low": 97.0,
                    "close": 98.5,
                    "volume": 1000.0,
                },
                {
                    "open_time": "2024-01-01T12:00:00Z",
                    "open": 99.0,
                    "high": 101.0,
                    "low": 98.0,
                    "close": 99.5,
                    "volume": 1000.0,
                },
            ]
        )
        sweeps = detect_sweeps([pool], df)
        assert len(sweeps) == 1
        assert sweeps[0].type == "bear"
        assert sweeps[0].pool_level == pytest.approx(100.0)
        assert sweeps[0].sweep_extreme == pytest.approx(102.0)
        assert pool.swept is True

    def test_bsl_not_swept_close_above(self) -> None:
        """High > level but close > level → NOT a sweep (close didn't return)."""
        pool = self._make_pool("BSL", 100.0)
        df = _candle_df(
            [
                {
                    "open_time": "2024-01-01T10:00:00Z",
                    "open": 99.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.5,
                    "volume": 1000.0,
                },
            ]
        )
        sweeps = detect_sweeps([pool], df)
        assert len(sweeps) == 0
        assert pool.swept is False

    def test_ssl_sweep_detected(self) -> None:
        """SSL swept: candle.low < level AND candle.close > level."""
        pool = self._make_pool("SSL", 50.0)
        df = _candle_df(
            [
                {
                    "open_time": "2024-01-01T10:00:00Z",
                    "open": 52.0,
                    "high": 53.0,
                    "low": 48.0,
                    "close": 51.5,
                    "volume": 1000.0,
                },
            ]
        )
        sweeps = detect_sweeps([pool], df)
        assert len(sweeps) == 1
        assert sweeps[0].type == "bull"
        assert sweeps[0].sweep_extreme == pytest.approx(48.0)

    def test_ssl_not_swept_close_below(self) -> None:
        """Low < level but close < level → NOT a sweep."""
        pool = self._make_pool("SSL", 50.0)
        df = _candle_df(
            [
                {
                    "open_time": "2024-01-01T10:00:00Z",
                    "open": 51.0,
                    "high": 52.0,
                    "low": 48.0,
                    "close": 49.0,
                    "volume": 1000.0,
                },
            ]
        )
        sweeps = detect_sweeps([pool], df)
        assert len(sweeps) == 0

    def test_sweep_starts_after_last_swing(self) -> None:
        """Sweep detection ignores candles before pool's last swing index."""
        pool = self._make_pool("BSL", 100.0, 4)  # last_idx=4 → start=5, df has 5 rows (0-4)
        # All 5 candles are at indices 0-4 < start=5 → skipped
        df = _candle_df(
            [
                {
                    "open_time": f"2024-01-01T{i:02d}:00:00Z",
                    "open": 98.0,
                    "high": 102.0,
                    "low": 97.0,
                    "close": 98.5,
                    "volume": 1000.0,
                }
                for i in range(5)
            ]
        )
        sweeps = detect_sweeps([pool], df)
        assert len(sweeps) == 0

    def test_only_first_sweep_recorded(self) -> None:
        """Pool swept only once — first occurrence only."""
        pool = self._make_pool("BSL", 100.0)
        df = _candle_df(
            [
                # Two candles that would both qualify as sweeps
                {
                    "open_time": "2024-01-01T10:00:00Z",
                    "open": 98.0,
                    "high": 102.0,
                    "low": 97.0,
                    "close": 98.5,
                    "volume": 1000.0,
                },
                {
                    "open_time": "2024-01-01T11:00:00Z",
                    "open": 98.0,
                    "high": 103.0,
                    "low": 97.0,
                    "close": 98.0,
                    "volume": 1000.0,
                },
            ]
        )
        sweeps = detect_sweeps([pool], df)
        assert len(sweeps) == 1
