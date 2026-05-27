from __future__ import annotations

import os
import time
from typing import Any

import httpx
import pandas as pd

BINANCE_API_BASE = os.getenv("BINANCE_API_BASE", "https://fapi.binance.com")
KLINES_ENDPOINT = "/fapi/v1/klines"
MAX_LIMIT = 1500  # Binance futures max per request

_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]
_KEEP_COLS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
]
_NUMERIC_COLS = ["open", "high", "low", "close", "volume", "quote_volume"]


def fetch_klines(
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    client: httpx.Client | None = None,
) -> pd.DataFrame:
    """Fetch klines from Binance for [start_ms, end_ms) range.

    Returns DataFrame with open_time as timestamp[ms, UTC].
    """
    rows: list[list[Any]] = []
    current_start = start_ms

    def _do_request(c: httpx.Client) -> None:
        nonlocal current_start
        while current_start < end_ms:
            params = {
                "symbol": symbol,
                "interval": interval,
                "startTime": current_start,
                "endTime": end_ms - 1,
                "limit": MAX_LIMIT,
            }
            resp = c.get(f"{BINANCE_API_BASE}{KLINES_ENDPOINT}", params=params, timeout=30.0)
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            rows.extend(batch)
            last_open_time = batch[-1][0]
            if last_open_time >= end_ms - 1:
                break
            current_start = last_open_time + 1
            if len(batch) < MAX_LIMIT:
                break
            time.sleep(0.05)

    if client is not None:
        _do_request(client)
    else:
        with httpx.Client() as c:
            _do_request(c)

    if not rows:
        return _empty_df()

    df = pd.DataFrame(rows, columns=_COLUMNS)
    df = df[_KEEP_COLS]
    for col in _NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["trades"] = pd.to_numeric(df["trades"], errors="coerce").astype("Int64")
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    df = df.sort_values("open_time").reset_index(drop=True)
    return df


def _empty_df() -> pd.DataFrame:
    df = pd.DataFrame(
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
        ]
    )
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], utc=True)
    return df
