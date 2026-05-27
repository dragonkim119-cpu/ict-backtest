"""Week 3: BPR (Balanced Price Range) 단위 테스트."""

from __future__ import annotations

import pandas as pd
import pytest

from app.models.patterns import FVG
from app.patterns.bpr import detect_bprs


def _fvg(
    ftype: str,
    bottom: float,
    top: float,
    mid_idx: int,
) -> FVG:
    t = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=mid_idx)
    return FVG(
        type=ftype,  # type: ignore[arg-type]
        bottom=bottom,
        top=top,
        start_index=mid_idx - 1,
        middle_index=mid_idx,
        end_index=mid_idx + 1,
        created_time=t,
    )


class TestDetectBPRs:
    def test_opposite_overlapping_fvgs_form_bpr(self) -> None:
        """Bull FVG then bear FVG with overlap → 1 BPR."""
        fvgs = [
            _fvg("bull", 100.0, 120.0, mid_idx=5),
            _fvg("bear", 110.0, 130.0, mid_idx=10),
        ]
        bprs = detect_bprs(fvgs)
        assert len(bprs) == 1
        assert bprs[0].type == "bear"
        assert bprs[0].bottom == pytest.approx(110.0)
        assert bprs[0].top == pytest.approx(120.0)

    def test_same_direction_no_bpr(self) -> None:
        """Two bull FVGs → no BPR (must be opposite directions)."""
        fvgs = [
            _fvg("bull", 100.0, 120.0, mid_idx=5),
            _fvg("bull", 110.0, 130.0, mid_idx=10),
        ]
        assert detect_bprs(fvgs) == []

    def test_no_overlap_no_bpr(self) -> None:
        """Bull FVG (100-110) and bear FVG (120-130) → no overlap → no BPR."""
        fvgs = [
            _fvg("bull", 100.0, 110.0, mid_idx=5),
            _fvg("bear", 120.0, 130.0, mid_idx=10),
        ]
        assert detect_bprs(fvgs) == []

    def test_insufficient_overlap_ratio_no_bpr(self) -> None:
        """Overlap exists but overlap/smaller < 0.3 → no BPR."""
        # smaller FVG height = 10; overlap = 1 → ratio = 0.1 < 0.3
        fvgs = [
            _fvg("bull", 100.0, 110.0, mid_idx=5),
            _fvg("bear", 109.0, 130.0, mid_idx=10),
        ]
        bprs = detect_bprs(fvgs, min_overlap_ratio=0.3)
        assert len(bprs) == 0

    def test_bpr_type_follows_newer_fvg(self) -> None:
        """BPR type = direction of the newer FVG."""
        fvgs = [
            _fvg("bear", 100.0, 120.0, mid_idx=5),
            _fvg("bull", 110.0, 130.0, mid_idx=10),
        ]
        bprs = detect_bprs(fvgs)
        assert len(bprs) == 1
        assert bprs[0].type == "bull"

    def test_too_old_fvg_excluded(self) -> None:
        """fvg_old beyond max_age_candles from fvg_new → not paired."""
        fvgs = [
            _fvg("bull", 100.0, 120.0, mid_idx=1),
            _fvg("bear", 110.0, 130.0, mid_idx=200),
        ]
        bprs = detect_bprs(fvgs, max_age_candles=100)
        assert len(bprs) == 0

    def test_bpr_created_index_is_fvg_new_end_index(self) -> None:
        """BPR created_index = fvg_new.end_index (confirmed, no lookahead)."""
        fvgs = [
            _fvg("bull", 100.0, 120.0, mid_idx=5),
            _fvg("bear", 110.0, 130.0, mid_idx=10),
        ]
        bprs = detect_bprs(fvgs)
        assert len(bprs) == 1
        assert bprs[0].created_index == 11  # fvg_new.end_index = mid+1 = 11

    def test_empty_fvgs(self) -> None:
        """Empty FVG list → no BPRs."""
        assert detect_bprs([]) == []

    def test_single_fvg_no_bpr(self) -> None:
        """One FVG cannot form a BPR."""
        fvgs = [_fvg("bull", 100.0, 120.0, mid_idx=5)]
        assert detect_bprs(fvgs) == []

    def test_multiple_bprs_from_multiple_pairs(self) -> None:
        """Two distinct opposite-FVG pairs → 2 BPRs."""
        fvgs = [
            _fvg("bull", 100.0, 120.0, mid_idx=5),
            _fvg("bear", 110.0, 130.0, mid_idx=10),
            _fvg("bull", 200.0, 220.0, mid_idx=50),
            _fvg("bear", 210.0, 230.0, mid_idx=55),
        ]
        bprs = detect_bprs(fvgs, max_age_candles=100)
        assert len(bprs) == 2
