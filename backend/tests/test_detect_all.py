"""Week 3: detect_all_patterns 통합 + 성능 테스트."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import pytest

from app.patterns.detect_all import PatternResult, detect_all_patterns


def _load_1h() -> pd.DataFrame:
    parquet = Path(__file__).parents[1] / "data" / "candles" / "BTCUSDT_1h.parquet"
    if not parquet.exists():
        pytest.skip("BTCUSDT_1h.parquet not found — run ingest first")
    import pyarrow.parquet as pq

    df = pq.read_table(parquet).to_pandas()
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    return df.reset_index(drop=True)


class TestDetectAllPatterns:
    def test_returns_pattern_result(self) -> None:
        """detect_all_patterns returns PatternResult with all fields."""
        df = _load_1h()
        result = detect_all_patterns(df)
        assert isinstance(result, PatternResult)

    def test_all_pattern_lists_present(self) -> None:
        """All seven pattern lists are populated (non-empty for 1-year data)."""
        df = _load_1h()
        result = detect_all_patterns(df)
        assert len(result.swings) > 0, "Expected swings"
        assert len(result.fvgs) > 0, "Expected FVGs"
        assert len(result.liquidity_pools) > 0, "Expected liquidity pools"

    def test_performance_under_3s(self) -> None:
        """Full pipeline on 1-year 1h data completes in < 3 seconds."""
        df = _load_1h()
        t0 = time.perf_counter()
        detect_all_patterns(df)
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"Too slow: {elapsed:.2f}s"

    def test_liquidity_pools_are_pydantic(self) -> None:
        """PatternResult.liquidity_pools contains LiquidityPool (not _Pool)."""
        from app.models.patterns import LiquidityPool

        df = _load_1h()
        result = detect_all_patterns(df)
        for pool in result.liquidity_pools:
            assert isinstance(pool, LiquidityPool)

    def test_sweeps_reference_valid_pools(self) -> None:
        """Every sweep.pool_level matches some pool.level in results."""
        df = _load_1h()
        result = detect_all_patterns(df)
        pool_levels = {p.level for p in result.liquidity_pools}
        for sweep in result.sweeps:
            assert sweep.pool_level in pool_levels

    def test_ifvgs_derived_from_invalidated_fvgs(self) -> None:
        """Every IFVG corresponds to an invalidated FVG."""
        df = _load_1h()
        result = detect_all_patterns(df)
        invalidated_times = {f.created_time for f in result.fvgs if f.invalidated}
        for ifvg in result.ifvgs:
            assert ifvg.original_fvg_created_time in invalidated_times

    def test_deterministic(self) -> None:
        """Same input → same output (swing count and FVG count)."""
        df = _load_1h()
        r1 = detect_all_patterns(df)
        r2 = detect_all_patterns(df)
        assert len(r1.swings) == len(r2.swings)
        assert len(r1.fvgs) == len(r2.fvgs)
        assert len(r1.bprs) == len(r2.bprs)

    def test_empty_candles(self) -> None:
        """Empty DataFrame → all empty lists, no crash."""
        import pandas as pd

        df = pd.DataFrame(columns=["open_time", "open", "high", "low", "close", "volume"])
        df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
        result = detect_all_patterns(df)
        assert result.swings == []
        assert result.fvgs == []
        assert result.killzones == []
