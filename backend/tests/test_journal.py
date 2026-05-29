from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.backtest.journal import (
    create_entry,
    delete_entry,
    get_entry,
    list_entries,
    update_entry,
)
from app.models.journal import JournalEntryCreate, JournalEntryUpdate


def _base(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


def _entry_data(**kwargs) -> JournalEntryCreate:
    defaults = dict(
        symbol="BTCUSDT",
        interval="1h",
        direction="long",
        entry_time=datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc),
        entry_price=65_000.0,
        sl=64_000.0,
        tp=68_000.0,
        notes="test entry",
        tags=["fvg", "killzone"],
    )
    defaults.update(kwargs)
    return JournalEntryCreate(**defaults)


# ── create ─────────────────────────────────────────────────────────

def test_create_returns_entry_with_id(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    entry = create_entry(_entry_data())
    assert entry.id > 0
    assert entry.symbol == "BTCUSDT"
    assert entry.direction == "long"
    assert entry.tags == ["fvg", "killzone"]


def test_create_preserves_optional_fields(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    data = _entry_data(
        exit_time=datetime(2024, 6, 1, 14, 0, tzinfo=timezone.utc),
        exit_price=67_500.0,
        result_pnl=2.5,
        rr=2.5,
        run_id="abc123",
    )
    entry = create_entry(data)
    assert entry.exit_price == 67_500.0
    assert entry.result_pnl == 2.5
    assert entry.run_id == "abc123"


def test_create_defaults_empty_notes_and_tags(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    data = JournalEntryCreate(
        interval="5m",
        direction="short",
        entry_time=datetime(2024, 6, 2, tzinfo=timezone.utc),
        entry_price=60_000.0,
    )
    entry = create_entry(data)
    assert entry.notes == ""
    assert entry.tags == []


# ── get ─────────────────────────────────────────────────────────────

def test_get_returns_none_for_missing(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    assert get_entry(9999) is None


def test_get_round_trips(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    created = create_entry(_entry_data())
    fetched = get_entry(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.entry_price == created.entry_price


# ── list ─────────────────────────────────────────────────────────────

def test_list_returns_all(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    create_entry(_entry_data())
    create_entry(_entry_data(direction="short", entry_price=66_000.0))
    entries = list_entries()
    assert len(entries) == 2


def test_list_filter_by_direction(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    create_entry(_entry_data(direction="long"))
    create_entry(_entry_data(direction="short"))
    longs = list_entries(direction="long")
    assert all(e.direction == "long" for e in longs)
    assert len(longs) == 1


def test_list_filter_by_interval(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    create_entry(_entry_data(interval="1h"))
    create_entry(_entry_data(interval="5m"))
    results = list_entries(interval="5m")
    assert len(results) == 1
    assert results[0].interval == "5m"


def test_list_respects_limit(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    for i in range(5):
        create_entry(_entry_data(entry_price=60_000.0 + i))
    results = list_entries(limit=3)
    assert len(results) == 3


def test_list_ordered_by_entry_time_desc(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    create_entry(_entry_data(entry_time=datetime(2024, 6, 1, tzinfo=timezone.utc)))
    create_entry(_entry_data(entry_time=datetime(2024, 6, 3, tzinfo=timezone.utc)))
    entries = list_entries()
    assert entries[0].entry_time >= entries[1].entry_time


# ── update ───────────────────────────────────────────────────────────

def test_update_partial_fields(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    entry = create_entry(_entry_data())
    updated = update_entry(entry.id, JournalEntryUpdate(notes="updated note", result_pnl=1.8))
    assert updated is not None
    assert updated.notes == "updated note"
    assert updated.result_pnl == 1.8
    assert updated.entry_price == entry.entry_price


def test_update_tags(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    entry = create_entry(_entry_data())
    updated = update_entry(entry.id, JournalEntryUpdate(tags=["bpr", "sweep"]))
    assert updated is not None
    assert updated.tags == ["bpr", "sweep"]


def test_update_returns_none_for_missing(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    result = update_entry(9999, JournalEntryUpdate(notes="x"))
    assert result is None


def test_update_no_fields_returns_unchanged(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    entry = create_entry(_entry_data())
    same = update_entry(entry.id, JournalEntryUpdate())
    assert same is not None
    assert same.notes == entry.notes


# ── delete ───────────────────────────────────────────────────────────

def test_delete_existing(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    entry = create_entry(_entry_data())
    assert delete_entry(entry.id) is True
    assert get_entry(entry.id) is None


def test_delete_missing_returns_false(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    assert delete_entry(9999) is False


def test_delete_removes_only_target(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    e1 = create_entry(_entry_data())
    e2 = create_entry(_entry_data(entry_price=70_000.0))
    delete_entry(e1.id)
    assert get_entry(e2.id) is not None
    assert len(list_entries()) == 1


# ── stats ─────────────────────────────────────────────────────────

def test_stats_empty_db(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    from app.backtest.journal import get_stats
    s = get_stats()
    assert s.closed_total == 0
    assert s.win_rate == 0.0
    assert s.by_weekday == []
    assert s.by_month == []


def test_stats_counts_only_closed_trades(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    from app.backtest.journal import get_stats
    # open trade (no result_pnl)
    create_entry(_entry_data())
    # closed win
    create_entry(_entry_data(result_pnl=2.0, rr=2.0))
    # closed loss
    create_entry(_entry_data(result_pnl=-1.0, rr=-1.0))
    s = get_stats()
    assert s.closed_total == 2
    assert s.wins == 1
    assert s.losses == 1
    assert s.win_rate == 0.5
    assert s.total_pnl_r == pytest.approx(1.0)


def test_stats_by_direction(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    from app.backtest.journal import get_stats
    create_entry(_entry_data(direction="long", result_pnl=2.0))
    create_entry(_entry_data(direction="long", result_pnl=-1.0))
    create_entry(_entry_data(direction="short", result_pnl=3.0))
    s = get_stats()
    dirs = {d.direction: d for d in s.by_direction}
    assert dirs["long"].total == 2
    assert dirs["long"].wins == 1
    assert dirs["short"].total == 1
    assert dirs["short"].wins == 1


def test_stats_by_interval(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    from app.backtest.journal import get_stats
    create_entry(_entry_data(interval="1h", result_pnl=1.0))
    create_entry(_entry_data(interval="5m", result_pnl=-1.0))
    s = get_stats()
    intervals = {i.interval: i for i in s.by_interval}
    assert "1h" in intervals
    assert "5m" in intervals


def test_compare_backtest_no_runs(monkeypatch, tmp_path):
    _base(monkeypatch, tmp_path)
    from app.backtest.journal import get_compare_backtest
    result = get_compare_backtest()
    assert result.backtest.total_runs == 0
    assert result.backtest.avg_win_rate is None
