from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.backtest.engine import get_run_detail
from app.backtest.journal import (
    create_entry,
    delete_entry,
    get_compare_backtest,
    get_entry,
    get_stats,
    list_entries,
    update_entry,
)
from app.models.journal import (
    JournalCompareResult,
    JournalEntry,
    JournalEntryCreate,
    JournalEntryUpdate,
    JournalStats,
    JournalVsBacktest,
)

router = APIRouter()


@router.get("/journal/stats", response_model=JournalStats)
def journal_stats() -> JournalStats:
    return get_stats()


@router.get("/journal/compare-backtest", response_model=JournalVsBacktest)
def journal_compare_backtest() -> JournalVsBacktest:
    return get_compare_backtest()


@router.post("/journal", response_model=JournalEntry, status_code=201)
def create_journal_entry(body: JournalEntryCreate) -> JournalEntry:
    return create_entry(body)


@router.get("/journal", response_model=list[JournalEntry])
def list_journal_entries(
    symbol: str | None = Query(None),
    interval: str | None = Query(None),
    direction: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[JournalEntry]:
    return list_entries(symbol=symbol, interval=interval, direction=direction, limit=limit)


@router.get("/journal/{entry_id}", response_model=JournalEntry)
def get_journal_entry(entry_id: int) -> JournalEntry:
    entry = get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Journal entry {entry_id} not found")
    return entry


@router.put("/journal/{entry_id}", response_model=JournalEntry)
def update_journal_entry(entry_id: int, body: JournalEntryUpdate) -> JournalEntry:
    entry = update_entry(entry_id, body)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Journal entry {entry_id} not found")
    return entry


@router.delete("/journal/{entry_id}", status_code=204)
def delete_journal_entry(entry_id: int) -> None:
    if not delete_entry(entry_id):
        raise HTTPException(status_code=404, detail=f"Journal entry {entry_id} not found")


@router.get("/journal/{entry_id}/compare", response_model=JournalCompareResult)
def compare_journal_entry(entry_id: int) -> JournalCompareResult:
    entry = get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Journal entry {entry_id} not found")

    run: dict | None = None
    trades: list[dict] | None = None
    if entry.run_id:
        detail = get_run_detail(entry.run_id)
        if detail is not None:
            run, trades = detail

    return JournalCompareResult(journal=entry, run=run, trades=trades)
