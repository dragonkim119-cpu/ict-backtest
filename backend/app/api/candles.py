from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.data.loader import load_candles
from app.models.candle import Candle

router = APIRouter()


class CandlesResponse(BaseModel):
    symbol: str
    interval: str
    candles: list[Candle]


@router.get("/candles", response_model=CandlesResponse)
def get_candles(
    symbol: str = Query("BTCUSDT"),
    interval: str = Query("1h"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
) -> CandlesResponse:
    try:
        df = load_candles(symbol, interval, start=start, end=end)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No parquet file for {symbol} {interval}. Run ingest first.",
        )
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No candles found for {symbol} {interval} in requested range.",
        )
    candles = [
        Candle(
            open_time=row["open_time"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
        )
        for _, row in df.iterrows()
    ]
    return CandlesResponse(symbol=symbol, interval=interval, candles=candles)
