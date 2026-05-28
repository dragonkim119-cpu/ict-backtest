from __future__ import annotations

from datetime import datetime

from app.models.patterns import BPR


def is_within_htf_bpr(
    price: float,
    entry_time: datetime,
    htf_bprs: list[BPR],
) -> bool:
    """True if price is inside an HTF BPR zone that was created before entry_time."""
    for bpr in htf_bprs:
        if bpr.created_time > entry_time:
            continue
        if bpr.bottom <= price <= bpr.top:
            return True
    return False
