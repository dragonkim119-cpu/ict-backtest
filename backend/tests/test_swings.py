"""Week 2: Swing High/Low 검출 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> pd.DataFrame:
    df = pd.read_csv(FIXTURES / name, parse_dates=["open_time"])
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df = df.reset_index(drop=True)
    return df


def _detect(name: str, N: int = 5):
    from app.patterns.swings import detect_swings

    return detect_swings(_load(name), N=N)


class TestDetectSwings:
    def test_monotone_up_has_no_swings(self) -> None:
        """Strictly increasing candles → 0 swings."""
        swings = _detect("monotone_up.csv")
        assert len(swings) == 0

    def test_pyramid_has_one_swing_high(self) -> None:
        """Pyramid (up then down) → exactly 1 swing high at center, 0 swing lows."""
        swings = _detect("swing_pyramid.csv")
        highs = [s for s in swings if s.type == "high"]
        lows = [s for s in swings if s.type == "low"]
        assert len(highs) == 1
        assert len(lows) == 0
        assert highs[0].index == 10
        assert highs[0].price == pytest.approx(100.0)

    def test_valley_has_one_swing_low(self) -> None:
        """V-shape (down then up) → exactly 1 swing low at center, 0 swing highs."""
        swings = _detect("swing_valley.csv")
        highs = [s for s in swings if s.type == "high"]
        lows = [s for s in swings if s.type == "low"]
        assert len(highs) == 0
        assert len(lows) == 1
        assert lows[0].index == 10
        assert lows[0].price == pytest.approx(45.0)

    def test_zigzag_swing_count(self) -> None:
        """W-shape (41 candles): 2 swing highs at i=10,30 and 1 swing low at i=20."""
        swings = _detect("zigzag.csv")
        highs = [s for s in swings if s.type == "high"]
        lows = [s for s in swings if s.type == "low"]
        assert len(highs) == 2
        assert len(lows) == 1
        high_indices = sorted(s.index for s in highs)
        assert high_indices == [10, 30]
        assert lows[0].index == 20

    def test_swing_high_price_correct(self) -> None:
        """Swing high price equals candles[i].high (not low/close)."""
        swings = _detect("zigzag.csv")
        df = _load("zigzag.csv")
        for s in swings:
            if s.type == "high":
                assert s.price == pytest.approx(df.iloc[s.index]["high"])
            else:
                assert s.price == pytest.approx(df.iloc[s.index]["low"])

    def test_swing_time_matches_open_time(self) -> None:
        """Swing time must equal candles[i].open_time."""
        swings = _detect("swing_pyramid.csv")
        df = _load("swing_pyramid.csv")
        for s in swings:
            expected = df.iloc[s.index]["open_time"]
            assert s.time == expected

    def test_edge_candles_not_swings(self) -> None:
        """Candles within N of the edges (i<N or i>=len-N) must not be swings."""
        swings = _detect("zigzag.csv")
        df = _load("zigzag.csv")
        N = 5
        n = len(df)
        for s in swings:
            assert N <= s.index < n - N, f"Swing at edge index {s.index}"

    def test_custom_n(self) -> None:
        """Smaller N detects more swings on zigzag data."""
        swings_n5 = _detect("zigzag.csv", N=5)
        swings_n2 = _detect("zigzag.csv", N=2)
        assert len(swings_n2) >= len(swings_n5)

    def test_performance_1year_1h(self) -> None:
        """detect_swings on 1-year 1h data completes in < 1 second."""
        import time

        parquet = Path(__file__).parents[1] / "data" / "candles" / "BTCUSDT_1h.parquet"
        if not parquet.exists():
            pytest.skip("BTCUSDT_1h.parquet not found — run ingest first")

        import pyarrow.parquet as pq

        df = pq.read_table(parquet).to_pandas()
        df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
        df = df.reset_index(drop=True)

        from app.patterns.swings import detect_swings

        t0 = time.perf_counter()
        swings = detect_swings(df)
        elapsed = time.perf_counter() - t0

        assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s"
        assert len(swings) > 0
