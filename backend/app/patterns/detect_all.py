from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.models.patterns import (
    BPR,
    FVG,
    IFVG,
    PO3,
    KillZoneSpan,
    LiquidityPool,
    MSSEvent,
    OrderBlock,
    Sweep,
    Swing,
)
from app.patterns.atr import compute_atr
from app.patterns.bpr import detect_bprs
from app.patterns.fvg import detect_fvgs, update_fvg_states
from app.patterns.ifvg import derive_ifvgs
from app.patterns.killzone import detect_killzones
from app.patterns.liquidity import _Pool, detect_liquidity_pools, detect_sweeps
from app.patterns.mss import detect_mss
from app.patterns.ob import detect_order_blocks
from app.patterns.po3 import detect_po3
from app.patterns.swings import detect_swings


@dataclass
class PatternResult:
    swings: list[Swing] = field(default_factory=list)
    fvgs: list[FVG] = field(default_factory=list)
    ifvgs: list[IFVG] = field(default_factory=list)
    liquidity_pools: list[LiquidityPool] = field(default_factory=list)
    sweeps: list[Sweep] = field(default_factory=list)
    bprs: list[BPR] = field(default_factory=list)
    killzones: list[KillZoneSpan] = field(default_factory=list)
    po3s: list[PO3] = field(default_factory=list)
    obs: list[OrderBlock] = field(default_factory=list)
    mss: list[MSSEvent] = field(default_factory=list)


def detect_all_patterns(
    candles: pd.DataFrame,
    swing_n: int = 5,
    atr_multiplier: float = 0.1,
    liquidity_tolerance: float = 0.001,
    liquidity_min_count: int = 2,
    bpr_max_age: int = 100,
    bpr_min_overlap: float = 0.3,
) -> PatternResult:
    """Run the full ICT pattern detection pipeline in dependency order.

    Order: Swing → FVG → FVG state update → IFVG → Liquidity Pool
           → Liquidity Sweep → BPR → Kill Zone
    """
    # 1. Swing High/Low
    swings = detect_swings(candles, N=swing_n)

    # 2. FVG + state update (needed for IFVG)
    fvgs = detect_fvgs(candles, atr_multiplier=atr_multiplier)
    update_fvg_states(fvgs, candles)

    # 3. IFVG (derives from invalidated FVGs)
    ifvgs = derive_ifvgs(fvgs)

    # 4. Liquidity Pool
    pools: list[_Pool] = detect_liquidity_pools(
        swings,
        tolerance=liquidity_tolerance,
        min_count=liquidity_min_count,
    )

    # 5. Liquidity Sweep (mutates pool.swept in-place)
    sweeps = detect_sweeps(pools, candles)

    # 6. BPR
    bprs = detect_bprs(fvgs, max_age_candles=bpr_max_age, min_overlap_ratio=bpr_min_overlap)

    # 7. Kill Zone
    killzones = detect_killzones(candles)

    # 8. PO3 (London + NY_AM) + OB — share computed ATR
    atr = compute_atr(candles)
    po3s = (
        detect_po3(candles, atr=atr, session="London")
        + detect_po3(candles, atr=atr, session="NY_AM")
    )

    # 9. Order Block
    obs = detect_order_blocks(candles, atr=atr, fvgs=fvgs)
    obs = [ob for ob in obs if not ob.invalidated]

    # 10. Market Structure Shift (BOS / CHoCH)
    mss = detect_mss(candles, swings)

    # Convert internal _Pool → Pydantic LiquidityPool
    liquidity_pools = [p.to_pydantic() for p in pools]

    return PatternResult(
        swings=swings,
        fvgs=fvgs,
        ifvgs=ifvgs,
        liquidity_pools=liquidity_pools,
        sweeps=sweeps,
        bprs=bprs,
        killzones=killzones,
        po3s=po3s,
        obs=obs,
        mss=mss,
    )
