from __future__ import annotations

from app.models.patterns import FVG, IFVG


def derive_ifvgs(fvgs: list[FVG]) -> list[IFVG]:
    """Convert invalidated FVGs to IFVGs (inverted direction).

    Bullish FVG invalidated → Bearish IFVG (now acts as resistance)
    Bearish FVG invalidated → Bullish IFVG (now acts as support)
    """
    return [
        IFVG(
            type="bear" if fvg.type == "bull" else "bull",
            bottom=fvg.bottom,
            top=fvg.top,
            created_time=fvg.invalidated_time,  # type: ignore[arg-type]
            original_fvg_created_time=fvg.created_time,
        )
        for fvg in fvgs
        if fvg.invalidated
    ]
