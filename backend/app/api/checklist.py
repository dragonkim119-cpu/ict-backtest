from __future__ import annotations

from datetime import timezone

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.data.loader import load_candles
from app.models.patterns import BPR, FVG, KillZoneSpan, Sweep, Swing
from app.patterns.atr import compute_atr
from app.patterns.detect_all import detect_all_patterns

router = APIRouter()

_LOOKBACK = 500
_SWEEP_LOOKBACK = 20
_SL_MAX_PCT = 0.03


class CheckItem(BaseModel):
    id: int
    label: str
    passed: bool
    detail: str = ""


class ChecklistResult(BaseModel):
    symbol: str
    interval: str
    htf_interval: str
    evaluated_at: str
    price: float
    checks: list[CheckItem]
    score: int


# ── individual checks ──────────────────────────────────────────────


def _check_killzone(last_ts: pd.Timestamp, killzones: list[KillZoneSpan]) -> CheckItem:
    dt = last_ts.to_pydatetime()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    for kz in killzones:
        if kz.start_time <= dt <= kz.end_time:
            return CheckItem(id=1, label="Kill Zone", passed=True, detail=kz.name)
    return CheckItem(id=1, label="Kill Zone", passed=False, detail="No active Kill Zone")


def _check_htf_zone(
    close: float,
    htf_bprs: list[BPR],
    htf_fvgs: list[FVG],
    atr_val: float,
) -> CheckItem:
    for bpr in htf_bprs:
        if bpr.bottom <= close <= bpr.top:
            return CheckItem(
                id=2,
                label="HTF BPR/FVG Zone",
                passed=True,
                detail=f"In {bpr.type} HTF BPR {bpr.bottom:.0f}–{bpr.top:.0f}",
            )
    for fvg in htf_fvgs:
        if fvg.mitigated or fvg.invalidated:
            continue
        if fvg.bottom <= close <= fvg.top:
            return CheckItem(
                id=2,
                label="HTF BPR/FVG Zone",
                passed=True,
                detail=f"In {fvg.type} HTF FVG {fvg.bottom:.0f}–{fvg.top:.0f}",
            )
        if atr_val > 0:
            mid = (fvg.top + fvg.bottom) / 2
            if abs(close - mid) <= atr_val * 0.5:
                return CheckItem(
                    id=2,
                    label="HTF BPR/FVG Zone",
                    passed=True,
                    detail=f"Near {fvg.type} HTF FVG mid {mid:.0f}",
                )
    if not htf_bprs and not htf_fvgs:
        return CheckItem(id=2, label="HTF BPR/FVG Zone", passed=False, detail="No HTF data")
    return CheckItem(id=2, label="HTF BPR/FVG Zone", passed=False, detail="Not near HTF zone")


def _check_sweep(sweeps: list[Sweep], total_candles: int) -> CheckItem:
    cutoff = total_candles - _SWEEP_LOOKBACK
    recent = [s for s in sweeps if s.sweep_index >= cutoff]
    if recent:
        s = recent[-1]
        return CheckItem(
            id=3,
            label="Liquidity Sweep",
            passed=True,
            detail=f"{s.type} sweep at {s.pool_level:.0f}",
        )
    return CheckItem(
        id=3,
        label="Liquidity Sweep",
        passed=False,
        detail=f"No sweep in last {_SWEEP_LOOKBACK} candles",
    )


def _check_bpr_close(close: float, bprs: list[BPR]) -> CheckItem:
    for bpr in bprs:
        if bpr.bottom <= close <= bpr.top:
            return CheckItem(
                id=4,
                label="BPR Close",
                passed=True,
                detail=f"In {bpr.type} BPR {bpr.bottom:.0f}–{bpr.top:.0f}",
            )
    return CheckItem(id=4, label="BPR Close", passed=False, detail="Close not in any BPR")


def _check_sl_distance(close: float, swings: list[Swing]) -> CheckItem:
    if not swings:
        return CheckItem(id=5, label="SL ≤ 3%", passed=False, detail="No swings found")
    nearest = min(swings, key=lambda s: abs(s.price - close))
    pct = abs(close - nearest.price) / close
    passed = pct <= _SL_MAX_PCT
    return CheckItem(
        id=5,
        label="SL ≤ 3%",
        passed=passed,
        detail=f"{pct * 100:.2f}% to swing {nearest.price:.0f}",
    )


def _check_tp_path_clear(close: float, bprs: list[BPR], swings: list[Swing]) -> CheckItem:
    if not swings:
        return CheckItem(id=6, label="TP Path Clear (1:3)", passed=False, detail="No swings for SL")
    nearest = min(swings, key=lambda s: abs(s.price - close))
    sl_dist = abs(close - nearest.price)
    if sl_dist == 0:
        return CheckItem(
            id=6, label="TP Path Clear (1:3)", passed=False, detail="SL distance is zero"
        )

    bull = nearest.type == "low"
    rr = 3.0
    tp = close + rr * sl_dist if bull else close - rr * sl_dist

    obstacles: list[BPR] = []
    for bpr in bprs:
        if bull and bpr.type == "bear" and close < bpr.bottom < tp:
            obstacles.append(bpr)
        elif not bull and bpr.type == "bull" and tp < bpr.top < close:
            obstacles.append(bpr)

    if obstacles:
        return CheckItem(
            id=6,
            label="TP Path Clear (1:3)",
            passed=False,
            detail=f"{len(obstacles)} obstacle BPR(s) before TP {tp:.0f}",
        )
    direction = "long" if bull else "short"
    return CheckItem(
        id=6,
        label="TP Path Clear (1:3)",
        passed=True,
        detail=f"Clear to TP {tp:.0f} ({direction})",
    )


def _check_mtf_direction(close: float, bprs: list[BPR], htf_bprs: list[BPR]) -> CheckItem:
    if not htf_bprs:
        return CheckItem(id=7, label="MTF Direction", passed=False, detail="No HTF BPR data")

    in_htf = [b for b in htf_bprs if b.bottom <= close <= b.top]
    htf_bpr = (
        in_htf[0]
        if in_htf
        else min(htf_bprs, key=lambda b: min(abs(close - b.top), abs(close - b.bottom)))
    )

    ltf_in = [b for b in bprs if b.bottom <= close <= b.top]
    if not ltf_in:
        return CheckItem(
            id=7,
            label="MTF Direction",
            passed=False,
            detail=f"Not in LTF BPR (HTF bias: {htf_bpr.type})",
        )
    ltf_bpr = ltf_in[0]
    matched = ltf_bpr.type == htf_bpr.type
    return CheckItem(
        id=7,
        label="MTF Direction",
        passed=matched,
        detail=f"HTF {htf_bpr.type} / LTF {ltf_bpr.type}",
    )


# ── endpoint ───────────────────────────────────────────────────────


@router.get("/checklist", response_model=ChecklistResult)
def get_checklist(
    symbol: str = Query("BTCUSDT"),
    interval: str = Query("5m"),
    htf_interval: str = Query("1h"),
) -> ChecklistResult:
    try:
        df = load_candles(symbol, interval)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No data for {symbol} {interval}. Run ingest first.",
        )
    df = df.tail(_LOOKBACK).reset_index(drop=True)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No candles for {symbol} {interval}.")

    result = detect_all_patterns(df)
    atr = compute_atr(df)
    atr_val = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0

    htf_bprs: list[BPR] = []
    htf_fvgs: list[FVG] = []
    if htf_interval and htf_interval != interval:
        try:
            htf_df = load_candles(symbol, htf_interval)
            htf_df = htf_df.tail(_LOOKBACK).reset_index(drop=True)
            if not htf_df.empty:
                htf_res = detect_all_patterns(htf_df)
                htf_bprs = htf_res.bprs
                htf_fvgs = htf_res.fvgs
        except FileNotFoundError:
            pass

    last = df.iloc[-1]
    close = float(last["close"])
    last_ts: pd.Timestamp = last["open_time"]
    evaluated_at = last_ts.isoformat()

    checks = [
        _check_killzone(last_ts, result.killzones),
        _check_htf_zone(close, htf_bprs, htf_fvgs, atr_val),
        _check_sweep(result.sweeps, len(df)),
        _check_bpr_close(close, result.bprs),
        _check_sl_distance(close, result.swings),
        _check_tp_path_clear(close, result.bprs, result.swings),
        _check_mtf_direction(close, result.bprs, htf_bprs),
    ]

    return ChecklistResult(
        symbol=symbol,
        interval=interval,
        htf_interval=htf_interval,
        evaluated_at=evaluated_at,
        price=close,
        checks=checks,
        score=sum(1 for c in checks if c.passed),
    )
