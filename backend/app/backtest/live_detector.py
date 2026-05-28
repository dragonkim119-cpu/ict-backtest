from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.data.loader import load_candles
from app.patterns.detect_all import detect_all_patterns

INTERVAL_MINUTES: dict[str, int] = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "1d": 1440,
}

LOOKBACK = 500


def _empty() -> dict:
    return {
        "fvgs": [],
        "ifvgs": [],
        "bprs": [],
        "sweeps": [],
        "liquidities": [],
        "killzones": [],
    }


def detect_live_patterns(symbol: str, interval: str) -> dict:
    """Load last LOOKBACK candles and run full pattern detection.

    Returns JSON-serializable dict for WebSocket transmission.
    """
    mins = INTERVAL_MINUTES.get(interval, 60)
    start = datetime.now(timezone.utc) - timedelta(minutes=int(mins * LOOKBACK * 1.1))
    try:
        candles = load_candles(symbol, interval, start=start)
    except FileNotFoundError:
        return _empty()
    if candles.empty:
        return _empty()

    candles = candles.tail(LOOKBACK).reset_index(drop=True)
    result = detect_all_patterns(candles)

    def _list(items: list) -> list:
        return [item.model_dump(mode="json") for item in items]

    return {
        "fvgs": _list(result.fvgs),
        "ifvgs": _list(result.ifvgs),
        "bprs": _list(result.bprs),
        "sweeps": _list(result.sweeps),
        "liquidities": _list(result.liquidity_pools),
        "killzones": _list(result.killzones),
    }
