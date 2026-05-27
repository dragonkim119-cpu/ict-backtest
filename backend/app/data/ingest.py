"""CLI: python -m app.data.ingest --symbol BTCUSDT --interval 1h --days 365"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.data.binance import fetch_klines  # noqa: E402
from app.data.loader import save_candles  # noqa: E402

VALID_INTERVALS = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"}


def ingest(symbol: str, interval: str, days: int) -> dict:
    """Fetch `days` worth of klines from Binance and upsert to Parquet.

    Returns dict with rows_written and latest_time.
    """
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Invalid interval: {interval}. Valid: {VALID_INTERVALS}")

    now = datetime.now(tz=timezone.utc)
    end_ms = int(now.timestamp() * 1000)
    start_ms = int((now - timedelta(days=days)).timestamp() * 1000)

    print(
        f"[ingest] {symbol} {interval} | {days}d | "
        f"{datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).isoformat()} → now"
    )

    t0 = time.perf_counter()
    df = fetch_klines(symbol=symbol, interval=interval, start_ms=start_ms, end_ms=end_ms)
    elapsed_fetch = time.perf_counter() - t0

    if df.empty:
        print("[ingest] No data returned from Binance.")
        return {"rows_written": 0, "latest_time": None}

    print(f"[ingest] Fetched {len(df):,} rows in {elapsed_fetch:.1f}s. Saving...")

    rows_written = save_candles(df, symbol, interval)
    latest_time = df["open_time"].max().isoformat()
    elapsed_total = time.perf_counter() - t0

    print(
        f"[ingest] Done. {rows_written:,} rows in parquet. "
        f"Latest: {latest_time}. Total: {elapsed_total:.1f}s"
    )
    return {"rows_written": rows_written, "latest_time": latest_time}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Binance klines to Parquet")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()
    ingest(symbol=args.symbol, interval=args.interval, days=args.days)


if __name__ == "__main__":
    main()
