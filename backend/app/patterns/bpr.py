from __future__ import annotations

from app.models.patterns import BPR, FVG
from app.patterns.config import BPR_MAX_AGE_CANDLES, BPR_MIN_OVERLAP_RATIO


def detect_bprs(
    fvgs: list[FVG],
    max_age_candles: int = BPR_MAX_AGE_CANDLES,
    min_overlap_ratio: float = BPR_MIN_OVERLAP_RATIO,
) -> list[BPR]:
    """Detect Balanced Price Ranges — overlapping opposite-direction FVG pairs.

    fvg_new's direction determines BPR direction.
    Only considers fvg_old within max_age_candles of fvg_new.
    Overlap must be >= min_overlap_ratio × smaller FVG height.
    Lookahead guard: BPR created_index = fvg_new.end_index (confirmed candle).
    """
    bprs: list[BPR] = []
    fvgs_sorted = sorted(fvgs, key=lambda f: f.middle_index)

    for i, fvg_new in enumerate(fvgs_sorted):
        for fvg_old in fvgs_sorted[:i]:
            if fvg_old.type == fvg_new.type:
                continue
            if fvg_new.middle_index - fvg_old.middle_index > max_age_candles:
                continue

            overlap_top = min(fvg_old.top, fvg_new.top)
            overlap_bottom = max(fvg_old.bottom, fvg_new.bottom)
            overlap = overlap_top - overlap_bottom
            if overlap <= 0:
                continue

            smaller = min(
                fvg_old.top - fvg_old.bottom,
                fvg_new.top - fvg_new.bottom,
            )
            if smaller <= 0 or overlap / smaller < min_overlap_ratio:
                continue

            bprs.append(
                BPR(
                    type=fvg_new.type,
                    top=float(overlap_top),
                    bottom=float(overlap_bottom),
                    fvg_old_time=fvg_old.created_time,
                    fvg_new_time=fvg_new.created_time,
                    created_time=fvg_new.created_time,
                    created_index=fvg_new.end_index,
                )
            )

    return bprs
