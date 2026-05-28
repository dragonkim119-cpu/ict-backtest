from __future__ import annotations

from datetime import datetime, timezone

from app.backtest.mtf_entry import is_within_htf_bpr
from app.models.patterns import BPR


def _bpr(bottom: float, top: float, created_ts: str = "2024-01-01T00:00:00") -> BPR:
    dt = datetime.fromisoformat(created_ts).replace(tzinfo=timezone.utc)
    return BPR(
        type="bull",
        bottom=bottom,
        top=top,
        fvg_old_time=dt,
        fvg_new_time=dt,
        created_time=dt,
        created_index=10,
    )


ENTRY_TIME = datetime(2024, 1, 2, tzinfo=timezone.utc)


def test_price_inside_single_bpr():
    bprs = [_bpr(100.0, 110.0)]
    assert is_within_htf_bpr(105.0, ENTRY_TIME, bprs) is True


def test_price_at_bottom_boundary():
    bprs = [_bpr(100.0, 110.0)]
    assert is_within_htf_bpr(100.0, ENTRY_TIME, bprs) is True


def test_price_at_top_boundary():
    bprs = [_bpr(100.0, 110.0)]
    assert is_within_htf_bpr(110.0, ENTRY_TIME, bprs) is True


def test_price_below_range():
    bprs = [_bpr(100.0, 110.0)]
    assert is_within_htf_bpr(99.9, ENTRY_TIME, bprs) is False


def test_price_above_range():
    bprs = [_bpr(100.0, 110.0)]
    assert is_within_htf_bpr(110.1, ENTRY_TIME, bprs) is False


def test_empty_htf_bprs():
    assert is_within_htf_bpr(105.0, ENTRY_TIME, []) is False


def test_htf_bpr_created_after_entry_ignored():
    future_bpr = _bpr(100.0, 110.0, created_ts="2024-01-03T00:00:00")
    assert is_within_htf_bpr(105.0, ENTRY_TIME, [future_bpr]) is False


def test_htf_bpr_created_same_time_as_entry_accepted():
    same_time_bpr = _bpr(100.0, 110.0, created_ts="2024-01-02T00:00:00")
    assert is_within_htf_bpr(105.0, ENTRY_TIME, [same_time_bpr]) is True


def test_multiple_bprs_first_miss_second_hit():
    bprs = [_bpr(200.0, 210.0), _bpr(100.0, 110.0)]
    assert is_within_htf_bpr(105.0, ENTRY_TIME, bprs) is True


def test_multiple_bprs_all_miss():
    bprs = [_bpr(200.0, 210.0), _bpr(300.0, 310.0)]
    assert is_within_htf_bpr(105.0, ENTRY_TIME, bprs) is False
