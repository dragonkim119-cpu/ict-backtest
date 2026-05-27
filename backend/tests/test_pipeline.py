"""Week 1 검증: 캔들 수집/저장/로드 round-trip 테스트."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _make_candle_df(n: int = 10, start_ms: int = 1_700_000_000_000) -> pd.DataFrame:
    """Create synthetic candle DataFrame matching the Parquet schema."""
    interval_ms = 3_600_000  # 1h in ms
    rows = []
    for i in range(n):
        ot = start_ms + i * interval_ms
        rows.append(
            {
                "open_time": pd.Timestamp(ot, unit="ms", tz="UTC"),
                "open": 40000.0 + i,
                "high": 40100.0 + i,
                "low": 39900.0 + i,
                "close": 40050.0 + i,
                "volume": 1000.0 + i,
                "close_time": pd.Timestamp(ot + interval_ms - 1, unit="ms", tz="UTC"),
                "quote_volume": 4e7 + i,
                "trades": 5000 + i,
            }
        )
    return pd.DataFrame(rows)


class TestSaveLoad:
    def test_round_trip(self, tmp_path: Path) -> None:
        """save then load returns identical rows."""
        with patch.dict(os.environ, {"DATA_DIR": str(tmp_path)}):
            from app.data import loader

            df = _make_candle_df(10)
            loader.save_candles(df, "BTCUSDT", "1h")
            loaded = loader.load_candles("BTCUSDT", "1h")

        assert len(loaded) == 10
        assert list(loaded.columns[:6]) == ["open_time", "open", "high", "low", "close", "volume"]
        assert loaded["open_time"].dt.tz is not None
        pd.testing.assert_series_equal(
            df["close"].reset_index(drop=True),
            loaded["close"].reset_index(drop=True),
        )

    def test_dedup_on_upsert(self, tmp_path: Path) -> None:
        """Duplicate open_time rows are removed on second save."""
        with patch.dict(os.environ, {"DATA_DIR": str(tmp_path)}):
            from app.data import loader

            df1 = _make_candle_df(5)
            df2 = _make_candle_df(5)
            loader.save_candles(df1, "BTCUSDT", "1h")
            loader.save_candles(df2, "BTCUSDT", "1h")
            loaded = loader.load_candles("BTCUSDT", "1h")

        assert len(loaded) == 5, "Duplicate rows must be removed"

    def test_append_new_candles(self, tmp_path: Path) -> None:
        """Second batch with new timestamps is appended without duplicates."""
        with patch.dict(os.environ, {"DATA_DIR": str(tmp_path)}):
            from app.data import loader

            start = 1_700_000_000_000
            interval_ms = 3_600_000
            df1 = _make_candle_df(5, start_ms=start)
            df2 = _make_candle_df(5, start_ms=start + 5 * interval_ms)
            loader.save_candles(df1, "BTCUSDT", "1h")
            loader.save_candles(df2, "BTCUSDT", "1h")
            loaded = loader.load_candles("BTCUSDT", "1h")

        assert len(loaded) == 10
        assert loaded["open_time"].is_monotonic_increasing

    def test_load_with_time_filter(self, tmp_path: Path) -> None:
        """load_candles start/end filter works correctly."""
        with patch.dict(os.environ, {"DATA_DIR": str(tmp_path)}):
            from app.data import loader

            df = _make_candle_df(24)
            loader.save_candles(df, "BTCUSDT", "1h")

            first_time = df["open_time"].iloc[0].isoformat()
            fifth_time = df["open_time"].iloc[4].isoformat()
            loaded = loader.load_candles("BTCUSDT", "1h", start=first_time, end=fifth_time)

        assert len(loaded) == 5

    def test_schema_columns(self, tmp_path: Path) -> None:
        """Loaded DataFrame has all required columns with correct types."""
        with patch.dict(os.environ, {"DATA_DIR": str(tmp_path)}):
            from app.data import loader

            df = _make_candle_df(3)
            loader.save_candles(df, "BTCUSDT", "1h")
            loaded = loader.load_candles("BTCUSDT", "1h")

        required = {"open_time", "open", "high", "low", "close", "volume"}
        assert required.issubset(set(loaded.columns))
        assert str(loaded["open"].dtype) == "float64"
        assert str(loaded["trades"].dtype) == "int64"

    def test_candle_count(self, tmp_path: Path) -> None:
        """candle_count returns row count without full load."""
        with patch.dict(os.environ, {"DATA_DIR": str(tmp_path)}):
            from app.data import loader

            df = _make_candle_df(7)
            loader.save_candles(df, "BTCUSDT", "1h")
            count = loader.candle_count("BTCUSDT", "1h")

        assert count == 7

    def test_file_not_found(self, tmp_path: Path) -> None:
        """load_candles raises FileNotFoundError when no parquet exists."""
        with patch.dict(os.environ, {"DATA_DIR": str(tmp_path)}):
            from app.data import loader

            with pytest.raises(FileNotFoundError):
                loader.load_candles("BTCUSDT", "5m")


class TestBinanceClient:
    """Lightweight unit tests for binance.py (no real network calls)."""

    def test_fetch_klines_empty_response(self) -> None:
        """Empty API response returns empty DataFrame."""
        from app.data.binance import fetch_klines

        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()

        with patch("app.data.binance.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.return_value = mock_resp
            df = fetch_klines("BTCUSDT", "1h", 1_700_000_000_000, 1_700_003_600_000)

        assert df.empty

    def test_fetch_klines_parses_row(self) -> None:
        """Single row from Binance is parsed to correct dtypes."""
        from app.data.binance import fetch_klines

        fake_row = [
            1_700_000_000_000,  # open_time ms
            "40000.00",  # open
            "40100.00",  # high
            "39900.00",  # low
            "40050.00",  # close
            "100.5",  # volume
            1_700_003_599_999,  # close_time ms
            "4020000.00",  # quote_volume
            "5000",  # trades
            "50.0",  # taker_buy_base
            "2010000.00",  # taker_buy_quote
            "0",  # ignore
        ]

        mock_resp = MagicMock()
        mock_resp.json.side_effect = [[fake_row], []]
        mock_resp.raise_for_status = MagicMock()

        with patch("app.data.binance.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.return_value = mock_resp
            df = fetch_klines("BTCUSDT", "1h", 1_700_000_000_000, 1_700_003_600_000)

        assert len(df) == 1
        assert df["close"].iloc[0] == pytest.approx(40050.0)
        assert df["trades"].iloc[0] == 5000
        assert df["open_time"].iloc[0].tzinfo is not None
