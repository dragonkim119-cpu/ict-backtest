from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from app.models.patterns import KillZoneSpan

# (name, start_hour, start_min, end_hour, end_min)
KILL_ZONES: list[tuple[str, int, int, int, int]] = [
    ("Asia", 23, 0, 4, 0),
    ("London", 2, 0, 5, 0),
    ("NY_AM", 13, 30, 16, 0),
    ("NY_PM", 18, 0, 20, 0),
]

_KZ_NAME = Literal["Asia", "London", "NY_AM", "NY_PM"]


def detect_killzones(candles: pd.DataFrame) -> list[KillZoneSpan]:
    """Label candle open_times by kill zone and return contiguous spans.

    Asia (23:00-04:00 UTC) crosses midnight — handled with OR logic.
    A span is a contiguous run of in-zone candles (index gap > 1 → new span).

    start_time = first candle's open_time, end_time = last candle's open_time.
    """
    if candles.empty:
        return []

    open_times_arr = candles["open_time"].to_numpy()
    hours = candles["open_time"].dt.hour.to_numpy(dtype=int)
    minutes = candles["open_time"].dt.minute.to_numpy(dtype=int)
    candle_mins = hours * 60 + minutes

    spans: list[KillZoneSpan] = []

    for kz_name, sh, sm, eh, em in KILL_ZONES:
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        crosses_midnight = end_min <= start_min

        if crosses_midnight:
            in_zone = (candle_mins >= start_min) | (candle_mins < end_min)
        else:
            in_zone = (candle_mins >= start_min) & (candle_mins < end_min)

        positions = np.where(in_zone)[0]
        if len(positions) == 0:
            continue

        span_start_pos = int(positions[0])
        prev_pos = int(positions[0])

        for pos in positions[1:]:
            pos = int(pos)
            if pos - prev_pos > 1:
                spans.append(
                    KillZoneSpan(
                        name=kz_name,  # type: ignore[arg-type]
                        start_time=pd.Timestamp(open_times_arr[span_start_pos]),
                        end_time=pd.Timestamp(open_times_arr[prev_pos]),
                    )
                )
                span_start_pos = pos
            prev_pos = pos

        spans.append(
            KillZoneSpan(
                name=kz_name,  # type: ignore[arg-type]
                start_time=pd.Timestamp(open_times_arr[span_start_pos]),
                end_time=pd.Timestamp(open_times_arr[prev_pos]),
            )
        )

    return spans
