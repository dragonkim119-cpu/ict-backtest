from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.data.loader import load_candles
from app.models.patterns import (
    BPR,
    FVG,
    IFVG,
    PO3,
    KillZoneSpan,
    LiquidityPool,
    Sweep,
    Swing,
)
from app.patterns.detect_all import detect_all_patterns

router = APIRouter()


class PatternsResponse(BaseModel):
    symbol: str
    interval: str
    swings: list[Swing]
    fvgs: list[FVG]
    ifvgs: list[IFVG]
    bprs: list[BPR]
    liquidities: list[LiquidityPool]
    sweeps: list[Sweep]
    killzones: list[KillZoneSpan]
    po3s: list[PO3]


@router.get("/patterns", response_model=PatternsResponse)
def get_patterns(
    symbol: str = Query("BTCUSDT"),
    interval: str = Query("1h"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
) -> PatternsResponse:
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
    result = detect_all_patterns(df)
    return PatternsResponse(
        symbol=symbol,
        interval=interval,
        swings=result.swings,
        fvgs=result.fvgs,
        ifvgs=result.ifvgs,
        bprs=result.bprs,
        liquidities=result.liquidity_pools,
        sweeps=result.sweeps,
        killzones=result.killzones,
        po3s=result.po3s,
    )
