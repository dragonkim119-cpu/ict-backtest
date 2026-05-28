from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.backtest.engine import run_backtest
from app.data.loader import load_candles
from app.models.patterns import BPR
from app.models.trade import Metrics, Trade
from app.patterns.detect_all import detect_all_patterns

router = APIRouter()


class BacktestResponse(BaseModel):
    run_id: str
    symbol: str
    interval: str
    trades: list[Trade]
    metrics: Metrics
    htf_bprs: list[BPR] = []


@router.post("/backtest", response_model=BacktestResponse)
def post_backtest(
    symbol: str = Query("BTCUSDT"),
    interval: str = Query("1h"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    kill_zone_only: bool = Query(False),
    require_sweep: bool = Query(False),
    htf_interval: str | None = Query(None),
) -> BacktestResponse:
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

    # MTF: load HTF candles and extract HTF BPRs for zone filtering
    htf_bprs: list[BPR] = []
    if htf_interval and htf_interval != interval:
        try:
            htf_df = load_candles(symbol, htf_interval, start=start, end=end)
            if not htf_df.empty:
                htf_result = detect_all_patterns(htf_df)
                htf_bprs = htf_result.bprs
        except FileNotFoundError:
            pass

    start_str = start.isoformat() if start else None
    end_str = end.isoformat() if end else None

    run_id, trades, metrics = run_backtest(
        symbol=symbol,
        interval=interval,
        candles=df,
        bprs=result.bprs,
        swings=result.swings,
        start=start_str,
        end=end_str,
        kill_zone_only=kill_zone_only,
        kill_zones=result.killzones,
        require_sweep=require_sweep,
        sweeps=result.sweeps,
        htf_interval=htf_interval,
        htf_bprs=htf_bprs if htf_bprs else None,
    )

    return BacktestResponse(
        run_id=run_id,
        symbol=symbol,
        interval=interval,
        trades=trades,
        metrics=metrics,
        htf_bprs=htf_bprs,
    )
