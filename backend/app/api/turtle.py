from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.data.loader import load_candles
from app.turtle.indicators import compute_donchian, extract_signals

router = APIRouter()


class DonchianPoint(BaseModel):
    time: str
    value: float


class TurtleSignal(BaseModel):
    time: str
    system: int
    type: str


class TurtleDonchianResponse(BaseModel):
    symbol: str
    interval: str
    s1_upper: list[DonchianPoint]
    s1_lower: list[DonchianPoint]
    s2_upper: list[DonchianPoint]
    s2_lower: list[DonchianPoint]
    signals: list[TurtleSignal]


def _to_points(df_col: object, times: object) -> list[DonchianPoint]:
    points = []
    for t, v in zip(times, df_col):
        if v != v:  # NaN
            continue
        ts = t.isoformat() if hasattr(t, "isoformat") else str(t)[:19] + "Z"
        points.append(DonchianPoint(time=ts, value=round(float(v), 2)))
    return points


@router.get("/turtle/donchian", response_model=TurtleDonchianResponse)
def get_turtle_donchian(
    symbol: str = Query("BTCUSDT"),
    interval: str = Query("1d"),
    start: str | None = Query(None),
    end: str | None = Query(None),
) -> TurtleDonchianResponse:
    try:
        df = load_candles(symbol, interval, start=start, end=end)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No data for {symbol} {interval}. Run ingest first.",
        )
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No candles for {symbol} {interval}.")

    df = compute_donchian(df)
    times = df["open_time"]

    return TurtleDonchianResponse(
        symbol=symbol,
        interval=interval,
        s1_upper=_to_points(df["s1_upper"], times),
        s1_lower=_to_points(df["s1_lower"], times),
        s2_upper=_to_points(df["s2_upper"], times),
        s2_lower=_to_points(df["s2_lower"], times),
        signals=[TurtleSignal(**s) for s in extract_signals(df)],
    )
