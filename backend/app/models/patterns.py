from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Swing(BaseModel):
    index: int
    type: Literal["high", "low"]
    price: float
    time: datetime


class FVG(BaseModel):
    model_config = ConfigDict(frozen=False)

    type: Literal["bull", "bear"]
    bottom: float
    top: float
    start_index: int
    middle_index: int
    end_index: int
    created_time: datetime
    mitigated: bool = False
    mitigated_time: datetime | None = None
    invalidated: bool = False
    invalidated_time: datetime | None = None


class IFVG(BaseModel):
    type: Literal["bull", "bear"]
    bottom: float
    top: float
    created_time: datetime
    original_fvg_created_time: datetime


class LiquidityPool(BaseModel):
    model_config = ConfigDict(frozen=False)

    side: Literal["BSL", "SSL"]
    level: float
    swing_times: list[datetime]
    swept: bool = False
    swept_time: datetime | None = None


class Sweep(BaseModel):
    type: Literal["bull", "bear"]
    pool_level: float
    sweep_index: int
    sweep_time: datetime
    sweep_extreme: float


class BPR(BaseModel):
    type: Literal["bull", "bear"]
    top: float
    bottom: float
    fvg_old_time: datetime
    fvg_new_time: datetime
    created_time: datetime
    created_index: int


class KillZoneSpan(BaseModel):
    name: Literal["Asia", "London", "NY_AM", "NY_PM"]
    start_time: datetime
    end_time: datetime


class PO3(BaseModel):
    session: Literal["London", "NY_AM"]
    type: Literal["bull", "bear"]
    accum_start_time: datetime
    accum_end_time: datetime
    accum_high: float
    accum_low: float
    manip_time: datetime
    manip_extreme: float
    distrib_start_time: datetime
    distrib_end_time: datetime | None = None


class OrderBlock(BaseModel):
    model_config = ConfigDict(frozen=False)

    type: Literal["bull", "bear"]
    top: float
    bottom: float
    ob_time: datetime
    ob_index: int
    created_time: datetime
    created_index: int
    mitigated: bool = False
    mitigated_time: datetime | None = None
    invalidated: bool = False
    invalidated_time: datetime | None = None
