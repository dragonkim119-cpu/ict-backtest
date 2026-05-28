from __future__ import annotations

from typing import Literal

import pandas as pd

from app.models.patterns import PO3
from app.patterns.po3 import detect_po3


def detect_amd(
    candles: pd.DataFrame,
    atr: pd.Series | None = None,
    session: Literal["London", "NY_AM"] = "NY_AM",
) -> list[PO3]:
    """AMD = PO3 without the tight-range Accumulation requirement."""
    return detect_po3(candles, atr=atr, session=session, accum_atr_threshold=None)
