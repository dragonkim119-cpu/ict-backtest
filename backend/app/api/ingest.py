from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.data.ingest import ingest

router = APIRouter()


class IngestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    days: int = 365


class IngestResponse(BaseModel):
    rows_written: int
    latest_time: str | None


@router.post("/ingest", response_model=IngestResponse)
def post_ingest(body: IngestRequest) -> IngestResponse:
    result = ingest(body.symbol, body.interval, body.days)
    return IngestResponse(
        rows_written=result["rows_written"],
        latest_time=result["latest_time"],
    )
