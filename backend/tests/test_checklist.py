from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from app.api.checklist import (
    _check_bpr_close,
    _check_htf_zone,
    _check_killzone,
    _check_mtf_direction,
    _check_sl_distance,
    _check_sweep,
    _check_tp_path_clear,
)
from app.models.patterns import BPR, FVG, KillZoneSpan, Sweep, Swing


def _bpr(t: str, bottom: float, top: float, created_ts: str = "2024-01-01T00:00:00") -> BPR:
    dt = datetime.fromisoformat(created_ts).replace(tzinfo=timezone.utc)
    return BPR(
        type=t, bottom=bottom, top=top,
        fvg_old_time=dt, fvg_new_time=dt, created_time=dt, created_index=10,
    )


def _fvg(t: str, bottom: float, top: float, mitigated: bool = False) -> FVG:
    dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return FVG(
        type=t, bottom=bottom, top=top,
        start_index=0, middle_index=1, end_index=2,
        created_time=dt, mitigated=mitigated,
    )


def _swing(t: str, price: float, idx: int = 10) -> Swing:
    return Swing(index=idx, type=t, price=price, time=datetime(2024, 1, 1, tzinfo=timezone.utc))


def _sweep(t: str, level: float, idx: int) -> Sweep:
    return Sweep(
        type=t, pool_level=level, sweep_index=idx,
        sweep_time=datetime(2024, 1, 1, tzinfo=timezone.utc), sweep_extreme=level,
    )


def _kz(name: str, start: str, end: str) -> KillZoneSpan:
    return KillZoneSpan(
        name=name,  # type: ignore[arg-type]
        start_time=datetime.fromisoformat(start).replace(tzinfo=timezone.utc),
        end_time=datetime.fromisoformat(end).replace(tzinfo=timezone.utc),
    )


# ── check 1: Kill Zone ─────────────────────────────────────────────

def test_killzone_inside():
    kz = _kz("NY_AM", "2024-01-01T13:30:00", "2024-01-01T16:00:00")
    ts = pd.Timestamp("2024-01-01T14:00:00", tz="UTC")
    item = _check_killzone(ts, [kz])
    assert item.passed and "NY_AM" in item.detail


def test_killzone_outside():
    kz = _kz("London", "2024-01-01T02:00:00", "2024-01-01T05:00:00")
    ts = pd.Timestamp("2024-01-01T12:00:00", tz="UTC")
    item = _check_killzone(ts, [kz])
    assert not item.passed


def test_killzone_empty():
    ts = pd.Timestamp("2024-01-01T14:00:00", tz="UTC")
    item = _check_killzone(ts, [])
    assert not item.passed


# ── check 2: HTF BPR/FVG Zone ─────────────────────────────────────

def test_htf_zone_inside_bpr():
    bpr = _bpr("bull", 100.0, 110.0)
    item = _check_htf_zone(105.0, [bpr], [], 50.0)
    assert item.passed and "BPR" in item.detail


def test_htf_zone_inside_fvg():
    fvg = _fvg("bull", 100.0, 110.0)
    item = _check_htf_zone(105.0, [], [fvg], 50.0)
    assert item.passed and "FVG" in item.detail


def test_htf_zone_near_fvg_midpoint():
    fvg = _fvg("bull", 100.0, 110.0)  # mid=105
    item = _check_htf_zone(106.0, [], [fvg], 100.0)  # within ATR*0.5=50
    assert item.passed


def test_htf_zone_mitigated_fvg_ignored():
    fvg = _fvg("bull", 100.0, 110.0, mitigated=True)
    item = _check_htf_zone(105.0, [], [fvg], 50.0)
    assert not item.passed


def test_htf_zone_miss():
    bpr = _bpr("bull", 200.0, 210.0)
    item = _check_htf_zone(100.0, [bpr], [], 50.0)
    assert not item.passed


# ── check 3: Liquidity Sweep ──────────────────────────────────────

def test_sweep_recent():
    s = _sweep("bull", 95000.0, 490)
    item = _check_sweep([s], 500)
    assert item.passed


def test_sweep_too_old():
    s = _sweep("bull", 95000.0, 400)  # 500-20=480, idx=400 → too old
    item = _check_sweep([s], 500)
    assert not item.passed


def test_sweep_empty():
    item = _check_sweep([], 100)
    assert not item.passed


# ── check 4: BPR Close ────────────────────────────────────────────

def test_bpr_close_inside():
    bpr = _bpr("bull", 100.0, 110.0)
    item = _check_bpr_close(105.0, [bpr])
    assert item.passed


def test_bpr_close_outside():
    bpr = _bpr("bull", 100.0, 110.0)
    item = _check_bpr_close(115.0, [bpr])
    assert not item.passed


# ── check 5: SL ≤ 3% ─────────────────────────────────────────────

def test_sl_within_limit():
    s = _swing("low", 97.0)
    item = _check_sl_distance(100.0, [s])
    assert item.passed  # 3% exact boundary


def test_sl_exceeds_limit():
    s = _swing("low", 96.0)
    item = _check_sl_distance(100.0, [s])
    assert not item.passed  # 4%


def test_sl_no_swings():
    item = _check_sl_distance(100.0, [])
    assert not item.passed


# ── check 6: TP Path Clear ────────────────────────────────────────

def test_tp_path_clear_no_obstacle():
    sl_swing = _swing("low", 98.0)  # bull, SL=2, TP=100+6=106
    item = _check_tp_path_clear(100.0, [], [sl_swing])
    assert item.passed


def test_tp_path_blocked():
    sl_swing = _swing("low", 98.0)  # bull, TP=106
    obstacle = _bpr("bear", 102.0, 104.0)  # bear BPR between 100 and 106
    item = _check_tp_path_clear(100.0, [obstacle], [sl_swing])
    assert not item.passed


def test_tp_path_clear_wrong_side_bpr_ignored():
    sl_swing = _swing("low", 98.0)  # bull
    non_obstacle = _bpr("bull", 102.0, 104.0)  # bull BPR doesn't block long TP
    item = _check_tp_path_clear(100.0, [non_obstacle], [sl_swing])
    assert item.passed


# ── check 7: MTF Direction ────────────────────────────────────────

def test_mtf_direction_match():
    htf = _bpr("bull", 100.0, 110.0)
    ltf = _bpr("bull", 102.0, 108.0)
    item = _check_mtf_direction(105.0, [ltf], [htf])
    assert item.passed


def test_mtf_direction_mismatch():
    htf = _bpr("bull", 100.0, 110.0)
    ltf = _bpr("bear", 102.0, 108.0)
    item = _check_mtf_direction(105.0, [ltf], [htf])
    assert not item.passed


def test_mtf_no_htf_data():
    ltf = _bpr("bull", 100.0, 110.0)
    item = _check_mtf_direction(105.0, [ltf], [])
    assert not item.passed


def test_mtf_not_in_ltf_bpr():
    htf = _bpr("bull", 100.0, 110.0)
    item = _check_mtf_direction(105.0, [], [htf])
    assert not item.passed
