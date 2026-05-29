from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PARQUET_SCHEMA = pa.schema(
    [
        pa.field("open_time", pa.timestamp("ms", tz="UTC")),
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("volume", pa.float64()),
        pa.field("close_time", pa.timestamp("ms", tz="UTC")),
        pa.field("quote_volume", pa.float64()),
        pa.field("trades", pa.int64()),
    ]
)


def _candles_dir() -> Path:
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    candles = data_dir / "candles"
    candles.mkdir(parents=True, exist_ok=True)
    return candles


def _parquet_path(symbol: str, interval: str) -> Path:
    return _candles_dir() / f"{symbol}_{interval}.parquet"


def save_candles(df: pd.DataFrame, symbol: str, interval: str) -> int:
    """Upsert candles into Parquet (dedup by open_time). Returns total row count."""
    path = _parquet_path(symbol, interval)

    if path.exists():
        existing = pq.read_table(path).to_pandas()
        existing["open_time"] = pd.to_datetime(existing["open_time"], utc=True)
        combined = pd.concat([existing, df], ignore_index=True)
    else:
        combined = df.copy()

    combined = (
        combined.drop_duplicates(subset=["open_time"], keep="last")
        .sort_values("open_time")
        .reset_index(drop=True)
    )

    combined["open_time"] = combined["open_time"].dt.tz_convert("UTC")
    combined["close_time"] = combined["close_time"].dt.tz_convert("UTC")
    for col in ["open", "high", "low", "close", "volume", "quote_volume"]:
        combined[col] = combined[col].astype("float64")
    combined["trades"] = combined["trades"].astype("int64")

    table = pa.Table.from_pandas(combined, schema=PARQUET_SCHEMA, preserve_index=False)
    pq.write_table(table, path, compression="snappy")
    return len(combined)


def _to_utc(value: str | datetime | pd.Timestamp | None) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def load_candles(
    symbol: str,
    interval: str,
    start: str | datetime | None = None,
    end: str | datetime | None = None,
) -> pd.DataFrame:
    """Load candles from Parquet. start/end accept ISO strings or datetime objects.

    Returns DataFrame sorted by open_time with RangeIndex.
    Columns: open_time, open, high, low, close, volume, close_time, quote_volume, trades
    """
    path = _parquet_path(symbol, interval)
    if not path.exists():
        raise FileNotFoundError(f"No parquet file for {symbol} {interval}: {path}")

    filters = []
    start_ts = _to_utc(start)
    end_ts = _to_utc(end)
    if start_ts is not None:
        filters.append(("open_time", ">=", start_ts))
    if end_ts is not None:
        filters.append(("open_time", "<=", end_ts))

    table = pq.read_table(path, filters=filters if filters else None)
    df = table.to_pandas()
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], utc=True)
    df = df.sort_values("open_time").reset_index(drop=True)
    return df


def get_candle_range(symbol: str, interval: str) -> dict | None:
    """Return {start, end, count} for stored candles, or None if no file."""
    path = _parquet_path(symbol, interval)
    if not path.exists():
        return None
    df = pq.read_table(path, columns=["open_time"]).to_pandas()
    if df.empty:
        return None
    ts = pd.to_datetime(df["open_time"], utc=True)
    return {
        "start": ts.min().isoformat(),
        "end": ts.max().isoformat(),
        "count": len(df),
    }


def candle_count(symbol: str, interval: str) -> int:
    """Return number of candles stored without loading full data."""
    path = _parquet_path(symbol, interval)
    if not path.exists():
        return 0
    meta = pq.read_metadata(path)
    return meta.num_rows
