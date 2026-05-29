from __future__ import annotations

import asyncio
import json

import pandas as pd
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.checklist import run_checklist
from app.backtest.live_detector import detect_live_patterns
from app.data.loader import save_candles
from app.data.ws_binance import KlineUpdate, stream_klines
from app.services.telegram import get_threshold, is_configured, send_message

router = APIRouter()

# LTF → HTF mapping for checklist evaluation
_HTF: dict[str, str] = {
    "1m": "5m",
    "3m": "15m",
    "5m": "1h",
    "15m": "1h",
    "30m": "4h",
    "1h": "4h",
    "4h": "1d",
}


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
    On candle close: saves to Parquet and sends updated pattern set.
    """
    await websocket.accept()
    try:
        async for update in stream_klines(symbol, interval):
            await websocket.send_text(_update_to_msg(update))
            if update.closed:
                asyncio.create_task(_on_close(update, websocket))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


async def _on_close(update: KlineUpdate, websocket: WebSocket) -> None:
    """Save closed candle to Parquet, then send pattern update via WS."""
    df = _to_df_row(update)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], utc=True)
    try:
        await asyncio.to_thread(save_candles, df, update.symbol, update.interval)
    except Exception:
        pass

    try:
        patterns = await asyncio.to_thread(detect_live_patterns, update.symbol, update.interval)
        msg = json.dumps({
            "type": "patterns",
            "symbol": update.symbol,
            "interval": update.interval,
            **patterns,
        })
        await websocket.send_text(msg)
    except Exception:
        pass

    if is_configured():
        asyncio.create_task(_check_and_alert(update))


async def _check_and_alert(update: KlineUpdate) -> None:
    """Evaluate checklist after candle close and send Telegram alert if threshold met."""
    try:
        htf = _HTF.get(update.interval, "1h")
        cl = await asyncio.to_thread(run_checklist, update.symbol, update.interval, htf)
        if cl is None or cl.score < get_threshold():
            return
        passed = ", ".join(c.label for c in cl.checks if c.passed)
        text = (
            f"\U0001f514 <b>ICT Alert</b> {update.symbol} {update.interval}\n"
            f"Score: <b>{cl.score}/7</b>\n"
            f"Price: {cl.price:,.2f}\n"
            f"Passed: {passed}\n"
            f"Time: {cl.evaluated_at}"
        )
        await send_message(text)
    except Exception:
        pass
