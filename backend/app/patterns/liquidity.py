from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import pandas as pd

from app.models.patterns import LiquidityPool, Sweep, Swing
from app.patterns.config import LIQUIDITY_MIN_COUNT, LIQUIDITY_TOLERANCE


@dataclass
class _Pool:
    """Internal pool with full Swing objects (needed for index tracking in sweep detection)."""

    side: Literal["BSL", "SSL"]
    level: float
    swings: list[Swing]
    swept: bool = False
    swept_time: datetime | None = None

    @property
    def last_swing_index(self) -> int:
        return max(s.index for s in self.swings)

    def to_pydantic(self) -> LiquidityPool:
        return LiquidityPool(
            side=self.side,
            level=self.level,
            swing_times=[s.time for s in self.swings],
            swept=self.swept,
            swept_time=self.swept_time,
        )


def detect_liquidity_pools(
    swings: list[Swing],
    tolerance: float = LIQUIDITY_TOLERANCE,
    min_count: int = LIQUIDITY_MIN_COUNT,
) -> list[_Pool]:
    """Detect BSL (Buy-Side) and SSL (Sell-Side) liquidity pools.

    BSL: cluster of swing highs at similar price levels (potential stops above)
    SSL: cluster of swing lows  at similar price levels (potential stops below)

    Tolerance: two swings are "equal" if |price diff| / price <= tolerance.
    min_count: minimum swings to form a pool.
    """
    pools: list[_Pool] = []

    for swing_type in ("high", "low"):
        sub = sorted(
            [s for s in swings if s.type == swing_type],
            key=lambda s: s.price,
        )
        if not sub:
            continue

        clusters: list[list[Swing]] = []
        current: list[Swing] = [sub[0]]

        for s in sub[1:]:
            ref_price = current[-1].price
            if ref_price > 0 and abs(s.price - ref_price) / ref_price <= tolerance:
                current.append(s)
            else:
                if len(current) >= min_count:
                    clusters.append(current)
                current = [s]
        if len(current) >= min_count:
            clusters.append(current)

        side: Literal["BSL", "SSL"] = "BSL" if swing_type == "high" else "SSL"
        for cluster in clusters:
            level = sum(s.price for s in cluster) / len(cluster)
            pools.append(_Pool(side=side, level=level, swings=cluster))

    return pools


def detect_sweeps(pools: list[_Pool], candles: pd.DataFrame) -> list[Sweep]:
    """Detect liquidity sweeps — price wicks through pool level then closes back.

    BSL sweep (bearish): candle.high > pool.level AND candle.close < pool.level
    SSL sweep (bullish): candle.low  < pool.level AND candle.close > pool.level

    Each pool can only be swept once (first occurrence, then tracking stops).
    Mutates pool.swept / pool.swept_time in-place.
    """
    if candles.empty:
        return []

    high = candles["high"].to_numpy(dtype=float)
    low = candles["low"].to_numpy(dtype=float)
    close = candles["close"].to_numpy(dtype=float)
    open_times = candles["open_time"].to_numpy()
    n = len(candles)
    sweeps: list[Sweep] = []

    for pool in pools:
        start = pool.last_swing_index + 1
        if start >= n:
            continue

        if pool.side == "BSL":
            mask = (high[start:] > pool.level) & (close[start:] < pool.level)
        else:
            mask = (low[start:] < pool.level) & (close[start:] > pool.level)

        if not mask.any():
            continue

        idx = start + int(mask.argmax())
        pool.swept = True
        pool.swept_time = pd.Timestamp(open_times[idx])

        if pool.side == "BSL":
            sweeps.append(
                Sweep(
                    type="bear",
                    pool_level=pool.level,
                    sweep_index=idx,
                    sweep_time=pd.Timestamp(open_times[idx]),
                    sweep_extreme=float(high[idx]),
                )
            )
        else:
            sweeps.append(
                Sweep(
                    type="bull",
                    pool_level=pool.level,
                    sweep_index=idx,
                    sweep_time=pd.Timestamp(open_times[idx]),
                    sweep_extreme=float(low[idx]),
                )
            )

    return sweeps
