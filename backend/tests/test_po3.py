"""Tests for PO3/AMD pattern detection."""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from app.patterns.amd import detect_amd
from app.patterns.po3 import detect_po3


def _candle(ts: str, o: float, h: float, lo: float, c: float) -> dict:
    return {"open_time": ts, "open": o, "high": h, "low": lo, "close": c, "volume": 1.0}


def _build_session(
    date: str = "2024-01-15",
    session: str = "NY_AM",
    accum_hours: int = 6,
    accum_range: float = 100.0,
    mid: float = 50000.0,
    warmup: int = 20,
    warmup_range: float = 500.0,
    add_manip: bool = True,
    manip_type: str = "bear",
    add_distrib: bool = True,
    distrib_move: float = 600.0,   # absolute price move for distribution candles
) -> pd.DataFrame:
    """Synthetic 1h-candle sequence for PO3 testing.

    Layout: [warmup] [accum_hours tight candles] [session: manip + distrib]
    The 20 warmup candles (range=500) give ATR≈500; accum candles are tight.
    """
    start_hour = 13 if session == "NY_AM" else 2
    start_min = 30 if session == "NY_AM" else 0
    sess_start = datetime.fromisoformat(
        f"{date}T{start_hour:02d}:{start_min:02d}:00+00:00"
    )

    rows: list[dict] = []

    # Warmup (for ATR bootstrap — not part of accumulation window)
    for i in range(warmup):
        t = sess_start - timedelta(hours=warmup + accum_hours - i)
        rows.append(_candle(
            t.isoformat(),
            mid, mid + warmup_range / 2, mid - warmup_range / 2, mid,
        ))

    # Accumulation (tight range before session)
    accum_high = mid + accum_range / 2
    accum_low = mid - accum_range / 2
    for i in range(accum_hours):
        t = sess_start - timedelta(hours=accum_hours - i)
        rows.append(_candle(t.isoformat(), mid, accum_high, accum_low, mid))

    # Session candles
    sess_t = sess_start
    if add_manip:
        if manip_type == "bear":
            # BSL sweep: wick above accum_high, close below
            rows.append(_candle(
                sess_t.isoformat(),
                mid, accum_high + 600, accum_low - 10, accum_high - 100,
            ))
        else:
            # SSL sweep: wick below accum_low, close above
            rows.append(_candle(
                sess_t.isoformat(),
                mid, accum_high + 10, accum_low - 600, accum_low + 100,
            ))
        sess_t += timedelta(hours=1)

    if add_distrib:
        for _ in range(3):
            if manip_type == "bear":
                rows.append(_candle(
                    sess_t.isoformat(),
                    mid, mid, mid - distrib_move, mid - distrib_move,
                ))
            else:
                rows.append(_candle(
                    sess_t.isoformat(),
                    mid, mid + distrib_move, mid, mid + distrib_move,
                ))
            sess_t += timedelta(hours=1)

    df = pd.DataFrame(rows)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df["close_time"] = df["open_time"]
    return df.reset_index(drop=True)


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestPO3Detection:
    def test_bear_po3_detected(self):
        """Tight accum + BSL sweep + downward distribution → 1 bear PO3."""
        df = _build_session(manip_type="bear", accum_range=100.0, distrib_move=600.0)
        # ATR ≈ 500 from warmup; accum_range=100 < 500*0.5=250 → passes
        # distrib_move=600 > 500*0.8=400 → distribution confirmed
        results = detect_po3(df, session="NY_AM")
        assert len(results) == 1
        assert results[0].type == "bear"
        assert results[0].session == "NY_AM"

    def test_bull_po3_detected(self):
        """Tight accum + SSL sweep + upward distribution → 1 bull PO3."""
        df = _build_session(manip_type="bull", accum_range=100.0, distrib_move=600.0)
        results = detect_po3(df, session="NY_AM")
        assert len(results) == 1
        assert results[0].type == "bull"

    def test_wide_accum_blocked_by_atr(self):
        """Accum range wider than ATR threshold → 0 PO3."""
        # ATR ≈ 500; accum_range=400 > 500*0.5=250 → blocked
        df = _build_session(manip_type="bear", accum_range=400.0, distrib_move=600.0)
        results = detect_po3(df, session="NY_AM")
        assert len(results) == 0

    def test_wide_accum_passes_amd(self):
        """AMD has no ATR threshold — detects where strict PO3 would reject."""
        # Use threshold=0.1: accum_range=100, ATR≈500 → 100 > 500*0.1=50 → PO3 fails
        df = _build_session(manip_type="bear", accum_range=100.0, distrib_move=600.0)
        results_po3 = detect_po3(df, session="NY_AM", accum_atr_threshold=0.1)
        assert len(results_po3) == 0  # strict threshold blocks it
        results_amd = detect_amd(df, session="NY_AM")
        assert len(results_amd) == 1  # AMD (no threshold) finds it

    def test_no_manipulation_sweep(self):
        """No sweep candle → 0 PO3."""
        df = _build_session(manip_type="bear", add_manip=False, add_distrib=False)
        assert detect_po3(df, session="NY_AM") == []

    def test_distribution_not_confirmed(self):
        """Sweep present but distribution move too small → 0 PO3."""
        # distrib_move=20 << ATR*0.8 ≈ 400 → not confirmed
        df = _build_session(manip_type="bear", distrib_move=20.0)
        assert detect_po3(df, session="NY_AM") == []

    def test_po3_fields_complete(self):
        """PO3 object has all expected fields populated correctly."""
        df = _build_session(manip_type="bull", accum_range=100.0, distrib_move=600.0)
        results = detect_po3(df, session="NY_AM")
        assert len(results) == 1
        p = results[0]
        assert p.accum_high > p.accum_low
        assert p.manip_extreme < p.accum_low  # bull sweep goes below accum_low
        assert p.distrib_start_time > p.manip_time
        assert p.distrib_end_time is not None
        assert p.distrib_end_time >= p.distrib_start_time

    def test_too_few_candles_no_crash(self):
        """Insufficient candles → empty result, no exception."""
        df = pd.DataFrame([{
            "open_time": pd.Timestamp("2024-01-15T14:00:00", tz="UTC"),
            "open": 50000, "high": 50100, "low": 49900, "close": 50050, "volume": 1.0,
        }])
        assert detect_po3(df, session="NY_AM") == []

    def test_london_session_label(self):
        """London session PO3 carries correct session label."""
        df = _build_session(
            date="2024-01-15", session="London",
            manip_type="bear", accum_range=100.0, distrib_move=600.0,
        )
        results = detect_po3(df, session="London")
        assert len(results) == 1
        assert results[0].session == "London"
