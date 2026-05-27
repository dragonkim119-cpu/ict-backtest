"""Week 2: FVG / IFVG 검출 단위 테스트."""

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


class TestDetectFVGs:
    def test_bull_fvg_detected(self) -> None:
        """bull_fvg.csv → exactly 1 bull FVG, 0 bear FVGs."""
        from app.patterns.fvg import detect_fvgs

        df = _load("bull_fvg.csv")
        fvgs = detect_fvgs(df)
        bulls = [f for f in fvgs if f.type == "bull"]
        bears = [f for f in fvgs if f.type == "bear"]
        assert len(bulls) == 1, f"Expected 1 bull FVG, got {len(bulls)}"
        assert len(bears) == 0

    def test_bull_fvg_range(self) -> None:
        """Bull FVG bottom/top match candle[16].high and candle[18].low."""
        from app.patterns.fvg import detect_fvgs

        df = _load("bull_fvg.csv")
        fvgs = detect_fvgs(df)
        fvg = next(f for f in fvgs if f.type == "bull")
        assert fvg.bottom == pytest.approx(df.iloc[16]["high"])  # c_prev.high = 100
        assert fvg.top == pytest.approx(df.iloc[18]["low"])  # c_curr.low  = 115

    def test_bull_fvg_indices(self) -> None:
        """Bull FVG start/middle/end indices point to correct candles."""
        from app.patterns.fvg import detect_fvgs

        df = _load("bull_fvg.csv")
        fvgs = detect_fvgs(df)
        fvg = next(f for f in fvgs if f.type == "bull")
        assert fvg.start_index == 16
        assert fvg.middle_index == 17
        assert fvg.end_index == 18
        assert fvg.created_time == df.iloc[17]["open_time"]

    def test_bear_fvg_detected(self) -> None:
        """bear_fvg.csv → exactly 1 bear FVG, 0 bull FVGs."""
        from app.patterns.fvg import detect_fvgs

        df = _load("bear_fvg.csv")
        fvgs = detect_fvgs(df)
        bulls = [f for f in fvgs if f.type == "bull"]
        bears = [f for f in fvgs if f.type == "bear"]
        assert len(bears) == 1, f"Expected 1 bear FVG, got {len(bears)}"
        assert len(bulls) == 0

    def test_bear_fvg_range(self) -> None:
        """Bear FVG bottom/top match candle[18].high and candle[16].low."""
        from app.patterns.fvg import detect_fvgs

        df = _load("bear_fvg.csv")
        fvgs = detect_fvgs(df)
        fvg = next(f for f in fvgs if f.type == "bear")
        assert fvg.bottom == pytest.approx(df.iloc[18]["high"])  # c_curr.high = 80
        assert fvg.top == pytest.approx(df.iloc[16]["low"])  # c_prev.low  = 100

    def test_fvg_defaults_unmitigated(self) -> None:
        """Newly detected FVG has mitigated=False, invalidated=False."""
        from app.patterns.fvg import detect_fvgs

        df = _load("bull_fvg.csv")
        fvgs = detect_fvgs(df)
        for fvg in fvgs:
            assert fvg.mitigated is False
            assert fvg.invalidated is False
            assert fvg.mitigated_time is None
            assert fvg.invalidated_time is None

    def test_performance_1year_1h(self) -> None:
        """detect_fvgs on 1-year 1h data completes in < 1 second."""
        import time
        from pathlib import Path

        parquet = Path(__file__).parents[1] / "data" / "candles" / "BTCUSDT_1h.parquet"
        if not parquet.exists():
            pytest.skip("BTCUSDT_1h.parquet not found — run ingest first")

        import pyarrow.parquet as pq

        df = pq.read_table(parquet).to_pandas()
        df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
        df = df.reset_index(drop=True)

        from app.patterns.fvg import detect_fvgs

        t0 = time.perf_counter()
        fvgs = detect_fvgs(df)
        elapsed = time.perf_counter() - t0

        assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s"
        assert len(fvgs) > 0


class TestUpdateFVGStates:
    def _make_flat_df(self, n: int, h: float = 100.0, lo: float = 95.0) -> pd.DataFrame:
        rows = []
        for i in range(n):
            rows.append(
                {
                    "open_time": pd.Timestamp(f"2024-01-01T{i:02d}:00:00Z", tz="UTC"),
                    "open": lo + 1,
                    "high": h,
                    "low": lo,
                    "close": lo + 3,
                    "volume": 1000.0,
                }
            )
        return pd.DataFrame(rows)

    def test_bull_fvg_mitigation(self) -> None:
        """After creating bull FVG, a candle whose low <= fvg.top triggers mitigation."""
        from app.models.patterns import FVG
        from app.patterns.fvg import update_fvg_states

        # Create a bull FVG manually: bottom=100, top=115
        fvg = FVG(
            type="bull",
            bottom=100.0,
            top=115.0,
            start_index=0,
            middle_index=1,
            end_index=2,
            created_time=pd.Timestamp("2024-01-01T01:00:00Z", tz="UTC"),
        )
        # Candles after FVG: first one dips to 113 (below top=115)
        rows = [
            {
                "open_time": pd.Timestamp(f"2024-01-01T0{i}:00:00Z", tz="UTC"),
                "open": 120.0,
                "high": 125.0,
                "low": 113.0,
                "close": 121.0,
                "volume": 1000.0,
            }
            if i == 3
            else {
                "open_time": pd.Timestamp(f"2024-01-01T0{i}:00:00Z", tz="UTC"),
                "open": 120.0,
                "high": 125.0,
                "low": 120.0,
                "close": 121.0,
                "volume": 1000.0,
            }
            for i in range(6)
        ]
        df = pd.DataFrame(rows)
        update_fvg_states([fvg], df)
        assert fvg.mitigated is True
        assert fvg.mitigated_time == df.iloc[3]["open_time"]
        assert fvg.invalidated is False

    def test_bull_fvg_invalidation_stops_tracking(self) -> None:
        """close < fvg.bottom → invalidated, tracking stops (mitigated_time unchanged)."""
        from app.models.patterns import FVG
        from app.patterns.fvg import update_fvg_states

        fvg = FVG(
            type="bull",
            bottom=100.0,
            top=115.0,
            start_index=0,
            middle_index=1,
            end_index=2,
            created_time=pd.Timestamp("2024-01-01T01:00:00Z", tz="UTC"),
        )
        rows = []
        for i in range(8):
            if i == 4:
                # Invalidation: close below bottom=100
                rows.append(
                    {
                        "open_time": pd.Timestamp(f"2024-01-01T0{i}:00:00Z", tz="UTC"),
                        "open": 95.0,
                        "high": 99.0,
                        "low": 90.0,
                        "close": 95.0,
                        "volume": 1000.0,
                    }
                )
            else:
                rows.append(
                    {
                        "open_time": pd.Timestamp(f"2024-01-01T0{i}:00:00Z", tz="UTC"),
                        "open": 116.0,
                        "high": 120.0,
                        "low": 116.0,
                        "close": 117.0,
                        "volume": 1000.0,
                    }
                )
        df = pd.DataFrame(rows)
        update_fvg_states([fvg], df)
        assert fvg.invalidated is True
        assert fvg.invalidated_time == df.iloc[4]["open_time"]

    def test_bear_fvg_mitigation(self) -> None:
        """Bear FVG: candle high >= fvg.bottom → mitigated."""
        from app.models.patterns import FVG
        from app.patterns.fvg import update_fvg_states

        fvg = FVG(
            type="bear",
            bottom=80.0,
            top=100.0,
            start_index=0,
            middle_index=1,
            end_index=2,
            created_time=pd.Timestamp("2024-01-01T01:00:00Z", tz="UTC"),
        )
        rows = [
            {
                "open_time": pd.Timestamp(f"2024-01-01T0{i}:00:00Z", tz="UTC"),
                "open": 75.0,
                "high": 81.0,
                "low": 70.0,
                "close": 76.0,
                "volume": 1000.0,
            }
            if i == 3
            else {
                "open_time": pd.Timestamp(f"2024-01-01T0{i}:00:00Z", tz="UTC"),
                "open": 70.0,
                "high": 75.0,
                "low": 65.0,
                "close": 71.0,
                "volume": 1000.0,
            }
            for i in range(6)
        ]
        df = pd.DataFrame(rows)
        update_fvg_states([fvg], df)
        assert fvg.mitigated is True
        assert fvg.mitigated_time == df.iloc[3]["open_time"]

    def test_bear_fvg_invalidation(self) -> None:
        """Bear FVG: close > fvg.top → invalidated."""
        from app.models.patterns import FVG
        from app.patterns.fvg import update_fvg_states

        fvg = FVG(
            type="bear",
            bottom=80.0,
            top=100.0,
            start_index=0,
            middle_index=1,
            end_index=2,
            created_time=pd.Timestamp("2024-01-01T01:00:00Z", tz="UTC"),
        )
        rows = []
        for i in range(6):
            if i == 4:
                rows.append(
                    {
                        "open_time": pd.Timestamp(f"2024-01-01T0{i}:00:00Z", tz="UTC"),
                        "open": 100.0,
                        "high": 110.0,
                        "low": 100.0,
                        "close": 105.0,
                        "volume": 1000.0,
                    }
                )
            else:
                rows.append(
                    {
                        "open_time": pd.Timestamp(f"2024-01-01T0{i}:00:00Z", tz="UTC"),
                        "open": 65.0,
                        "high": 70.0,
                        "low": 60.0,
                        "close": 65.0,
                        "volume": 1000.0,
                    }
                )
        df = pd.DataFrame(rows)
        update_fvg_states([fvg], df)
        assert fvg.invalidated is True
        assert fvg.invalidated_time == df.iloc[4]["open_time"]


class TestDeriveIFVGs:
    def test_invalidated_bull_becomes_bear_ifvg(self) -> None:
        """Invalidated bull FVG → bear IFVG with same price range."""
        from app.models.patterns import FVG
        from app.patterns.ifvg import derive_ifvgs

        fvg = FVG(
            type="bull",
            bottom=100.0,
            top=115.0,
            start_index=0,
            middle_index=1,
            end_index=2,
            created_time=pd.Timestamp("2024-01-01T01:00:00Z", tz="UTC"),
            invalidated=True,
            invalidated_time=pd.Timestamp("2024-01-01T05:00:00Z", tz="UTC"),
        )
        ifvgs = derive_ifvgs([fvg])
        assert len(ifvgs) == 1
        assert ifvgs[0].type == "bear"
        assert ifvgs[0].bottom == pytest.approx(100.0)
        assert ifvgs[0].top == pytest.approx(115.0)
        assert ifvgs[0].original_fvg_created_time == fvg.created_time

    def test_non_invalidated_fvg_skipped(self) -> None:
        """Non-invalidated FVG → no IFVG generated."""
        from app.models.patterns import FVG
        from app.patterns.ifvg import derive_ifvgs

        fvg = FVG(
            type="bull",
            bottom=100.0,
            top=115.0,
            start_index=0,
            middle_index=1,
            end_index=2,
            created_time=pd.Timestamp("2024-01-01T01:00:00Z", tz="UTC"),
        )
        assert derive_ifvgs([fvg]) == []
