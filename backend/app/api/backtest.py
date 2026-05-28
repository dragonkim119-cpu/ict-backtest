from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.backtest.engine import get_run_detail, list_runs, run_backtest
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


# ── run history ────────────────────────────────────────────────────


class StoredTrade(BaseModel):
    entry_index: int
    entry_time: str
    entry_price: float
    direction: Literal["long", "short"]
    sl: float
    tp: float
    exit_index: int
    exit_time: str
    exit_price: float
    status: Literal["closed_win", "closed_loss", "closed_timeout"]
    pnl_r: float


class BacktestRun(BaseModel):
    run_id: str
    symbol: str
    interval: str
    start_time: str | None
    end_time: str | None
    params_hash: str
    params_json: str
    total_trades: int
    wins: int
    losses: int
    timeouts: int
    win_rate: float
    profit_factor: float | None
    expectancy: float
    total_pnl_r: float
    max_drawdown_r: float
    max_consecutive_losses: int
    avg_trade_duration_candles: float
    created_at: str


class RunDetailResponse(BaseModel):
    run: BacktestRun
    trades: list[StoredTrade]


@router.get("/backtest/runs", response_model=list[BacktestRun])
def get_runs(limit: int = Query(50, ge=1, le=200)) -> list[BacktestRun]:
    rows = list_runs(limit)
    return [BacktestRun(**r) for r in rows]


@router.get("/backtest/runs/{run_id}", response_model=RunDetailResponse)
def get_run(run_id: str) -> RunDetailResponse:
    result = get_run_detail(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found.")
    run_dict, trades_list = result
    return RunDetailResponse(
        run=BacktestRun(**run_dict),
        trades=[StoredTrade(**t) for t in trades_list],
    )
