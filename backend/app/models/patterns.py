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
