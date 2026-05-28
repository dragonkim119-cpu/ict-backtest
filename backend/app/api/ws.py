from __future__ import annotations

import asyncio
import json

import pandas as pd
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.data.loader import save_candles
from app.data.ws_binance import KlineUpdate, stream_klines

router = APIRouter()


def _update_to_msg(u: KlineUpdate) -> str:
    return json.dumps({
        "type": "kline",
        "symbol": u.symbol,
        "interval": u.interval,
        "candle": {
            "open_time": u.open_time.isoformat(),
            "open": u.open,
            "high": u.high,
            "low": u.low,
            "close": u.close,
            "volume": u.volume,
            "closed": u.closed,
        },
    })


def _to_df_row(u: KlineUpdate) -> pd.DataFrame:
    return pd.DataFrame([{
        "open_time": pd.Timestamp(u.open_time),
        "open": u.open,
        "high": u.high,
        "low": u.low,
        "close": u.close,
        "volume": u.volume,
        "close_time": pd.Timestamp(u.close_time),
        "quote_volume": 0.0,
        "trades": 0,
    }])


@router.websocket("/ws/kline")
async def kline_ws(
    websocket: WebSocket,
    symbol: str = "BTCUSDT",
    interval: str = "1h",
) -> None:
    """Stream real-time kline updates to the client.

    Query params: symbol (default BTCUSDT), interval (default 1h)
    """
    await websocket.accept()
    try:
        async for update in stream_klines(symbol, interval):
            # Forward to frontend
            await websocket.send_text(_update_to_msg(update))

            # Persist closed candle to Parquet (fire-and-forget)
            if update.closed:
                asyncio.create_task(_save(update))

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


async def _save(update: KlineUpdate) -> None:
    df = _to_df_row(update)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], utc=True)
    try:
        save_candles(df, update.symbol, update.interval)
    except Exception:
        pass
