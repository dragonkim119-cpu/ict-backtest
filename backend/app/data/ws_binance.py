from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime, timezone

import websockets

# Spot stream (accessible globally). Futures: wss://fstream.binance.com/ws
BINANCE_WS_BASE = "wss://stream.binance.com:9443/ws"


@dataclass
class KlineUpdate:
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool  # True = candle is finalized


def _parse(raw: dict) -> KlineUpdate | None:
    if raw.get("e") != "kline":
        return None
    k = raw["k"]
    return KlineUpdate(
        symbol=raw["s"],
        interval=k["i"],
        open_time=datetime.fromtimestamp(k["t"] / 1000, tz=timezone.utc),
        close_time=datetime.fromtimestamp(k["T"] / 1000, tz=timezone.utc),
        open=float(k["o"]),
        high=float(k["h"]),
        low=float(k["l"]),
        close=float(k["c"]),
        volume=float(k["v"]),
        closed=bool(k["x"]),
    )


async def stream_klines(
    symbol: str,
    interval: str,
    reconnect_delay: float = 3.0,
) -> AsyncGenerator[KlineUpdate, None]:
    """Async generator yielding KlineUpdate from Binance futures stream.

    Auto-reconnects on disconnect.
    """
    url = f"{BINANCE_WS_BASE}/{symbol.lower()}@kline_{interval}"
    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                async for raw_msg in ws:
                    data = json.loads(raw_msg)
                    update = _parse(data)
                    if update is not None:
                        yield update
        except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError):
            await asyncio.sleep(reconnect_delay)
        except Exception:
            await asyncio.sleep(reconnect_delay)
