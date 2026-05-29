from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.models.journal import (
    BacktestAggregate,
    DirectionStat,
    HourStat,
    IntervalStat,
    JournalEntry,
    JournalEntryCreate,
    JournalEntryUpdate,
    JournalStats,
    JournalVsBacktest,
    MonthStat,
    WeekdayStat,
)

_COLS = (
    "id", "symbol", "interval", "direction",
    "entry_time", "exit_time", "entry_price", "exit_price",
    "sl", "tp", "result_pnl", "rr",
    "notes", "tags", "run_id", "created_at",
)


def _db_path() -> Path:
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "backtest.db"


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trade_journal (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT NOT NULL,
            interval    TEXT NOT NULL,
            direction   TEXT NOT NULL,
            entry_time  TEXT NOT NULL,
            exit_time   TEXT,
            entry_price REAL NOT NULL,
            exit_price  REAL,
            sl          REAL,
            tp          REAL,
            result_pnl  REAL,
            rr          REAL,
            notes       TEXT DEFAULT '',
            tags        TEXT DEFAULT '[]',
            run_id      TEXT,
            created_at  TEXT NOT NULL
        );
    """)
    conn.commit()


def _row_to_entry(row: tuple) -> JournalEntry:
    d = dict(zip(_COLS, row))
    d["tags"] = json.loads(d["tags"] or "[]")
    return JournalEntry(**d)


def create_entry(data: JournalEntryCreate) -> JournalEntry:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_db_path()) as conn:
        _ensure_table(conn)
        cur = conn.execute(
            """INSERT INTO trade_journal
               (symbol, interval, direction, entry_time, exit_time,
                entry_price, exit_price, sl, tp, result_pnl, rr,
                notes, tags, run_id, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data.symbol, data.interval, data.direction,
                data.entry_time.isoformat(),
                data.exit_time.isoformat() if data.exit_time else None,
                data.entry_price, data.exit_price,
                data.sl, data.tp, data.result_pnl, data.rr,
                data.notes, json.dumps(data.tags), data.run_id,
                now,
            ),
        )
        conn.commit()
        row_id: int = cur.lastrowid  # type: ignore[assignment]
    entry = get_entry(row_id)
    assert entry is not None
    return entry


def list_entries(
    symbol: str | None = None,
    interval: str | None = None,
    direction: str | None = None,
    limit: int = 100,
) -> list[JournalEntry]:
    with sqlite3.connect(_db_path()) as conn:
        _ensure_table(conn)
        cols_sql = ", ".join(_COLS)
        clauses: list[str] = []
        params: list = []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol)
        if interval:
            clauses.append("interval = ?")
            params.append(interval)
        if direction:
            clauses.append("direction = ?")
            params.append(direction)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        rows = conn.execute(
            f"SELECT {cols_sql} FROM trade_journal {where} ORDER BY entry_time DESC LIMIT ?",
            params,
        ).fetchall()
    return [_row_to_entry(r) for r in rows]


def get_entry(entry_id: int) -> JournalEntry | None:
    with sqlite3.connect(_db_path()) as conn:
        _ensure_table(conn)
        cols_sql = ", ".join(_COLS)
        row = conn.execute(
            f"SELECT {cols_sql} FROM trade_journal WHERE id = ?", (entry_id,)
        ).fetchone()
    if row is None:
        return None
    return _row_to_entry(row)


def update_entry(entry_id: int, data: JournalEntryUpdate) -> JournalEntry | None:
    raw = data.model_dump(exclude_none=True)
    if not raw:
        return get_entry(entry_id)
    if "tags" in raw:
        raw["tags"] = json.dumps(raw["tags"])
    if "exit_time" in raw and isinstance(raw["exit_time"], datetime):
        raw["exit_time"] = raw["exit_time"].isoformat()
    set_sql = ", ".join(f"{k} = ?" for k in raw)
    params = list(raw.values()) + [entry_id]
    with sqlite3.connect(_db_path()) as conn:
        _ensure_table(conn)
        conn.execute(f"UPDATE trade_journal SET {set_sql} WHERE id = ?", params)
        conn.commit()
    return get_entry(entry_id)


def delete_entry(entry_id: int) -> bool:
    with sqlite3.connect(_db_path()) as conn:
        _ensure_table(conn)
        cur = conn.execute("DELETE FROM trade_journal WHERE id = ?", (entry_id,))
        conn.commit()
        return cur.rowcount > 0


# ── stats ──────────────────────────────────────────────────────────

_WEEKDAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def _win_rate(wins: int, total: int) -> float:
    return round(wins / total, 4) if total > 0 else 0.0


def get_stats() -> JournalStats:
    with sqlite3.connect(_db_path()) as conn:
        _ensure_table(conn)

        # Overall
        row = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN result_pnl > 0 THEN 1 ELSE 0 END) as wins,
                AVG(rr) as avg_rr,
                COALESCE(SUM(result_pnl), 0) as total_pnl_r
            FROM trade_journal
            WHERE result_pnl IS NOT NULL
        """).fetchone()
        total, wins, avg_rr, total_pnl_r = row
        total = total or 0
        wins = wins or 0

        # By weekday
        wd_rows = conn.execute("""
            SELECT
                strftime('%w', entry_time) as dow,
                COUNT(*) as total,
                SUM(CASE WHEN result_pnl > 0 THEN 1 ELSE 0 END) as wins
            FROM trade_journal
            WHERE result_pnl IS NOT NULL
            GROUP BY dow
            ORDER BY dow
        """).fetchall()
        by_weekday = [
            WeekdayStat(
                day=_WEEKDAY_NAMES[int(r[0])],
                total=r[1], wins=r[2],
                win_rate=_win_rate(r[2], r[1]),
            )
            for r in wd_rows
        ]

        # By hour
        hr_rows = conn.execute("""
            SELECT
                CAST(strftime('%H', entry_time) AS INTEGER) as hour,
                COUNT(*) as total,
                SUM(CASE WHEN result_pnl > 0 THEN 1 ELSE 0 END) as wins
            FROM trade_journal
            WHERE result_pnl IS NOT NULL
            GROUP BY hour
            ORDER BY hour
        """).fetchall()
        by_hour = [
            HourStat(hour=r[0], total=r[1], wins=r[2], win_rate=_win_rate(r[2], r[1]))
            for r in hr_rows
        ]

        # By month
        mo_rows = conn.execute("""
            SELECT
                strftime('%Y-%m', entry_time) as month,
                COUNT(*) as total,
                SUM(CASE WHEN result_pnl > 0 THEN 1 ELSE 0 END) as wins,
                COALESCE(SUM(result_pnl), 0) as pnl_r
            FROM trade_journal
            WHERE result_pnl IS NOT NULL
            GROUP BY month
            ORDER BY month
        """).fetchall()
        by_month = [
            MonthStat(month=r[0], total=r[1], wins=r[2], pnl_r=round(r[3], 4))
            for r in mo_rows
        ]

        # By direction
        dir_rows = conn.execute("""
            SELECT
                direction,
                COUNT(*) as total,
                SUM(CASE WHEN result_pnl > 0 THEN 1 ELSE 0 END) as wins,
                AVG(result_pnl) as avg_pnl_r
            FROM trade_journal
            WHERE result_pnl IS NOT NULL
            GROUP BY direction
        """).fetchall()
        by_direction = [
            DirectionStat(
                direction=r[0], total=r[1], wins=r[2],
                win_rate=_win_rate(r[2], r[1]),
                avg_pnl_r=round(r[3], 4) if r[3] is not None else None,
            )
            for r in dir_rows
        ]

        # By interval
        iv_rows = conn.execute("""
            SELECT
                "interval",
                COUNT(*) as total,
                SUM(CASE WHEN result_pnl > 0 THEN 1 ELSE 0 END) as wins
            FROM trade_journal
            WHERE result_pnl IS NOT NULL
            GROUP BY "interval"
            ORDER BY total DESC
        """).fetchall()
        by_interval = [
            IntervalStat(interval=r[0], total=r[1], wins=r[2], win_rate=_win_rate(r[2], r[1]))
            for r in iv_rows
        ]

    return JournalStats(
        closed_total=total,
        wins=wins,
        losses=total - wins,
        win_rate=_win_rate(wins, total),
        avg_rr=round(avg_rr, 4) if avg_rr is not None else None,
        total_pnl_r=round(total_pnl_r, 4),
        by_weekday=by_weekday,
        by_hour=by_hour,
        by_month=by_month,
        by_direction=by_direction,
        by_interval=by_interval,
    )


def get_compare_backtest() -> JournalVsBacktest:
    journal_stats = get_stats()

    total_runs = 0
    avg_win_rate = None
    avg_pf = None
    avg_pnl_r = None

    db = _db_path()
    try:
        with sqlite3.connect(db) as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_runs,
                    AVG(win_rate) as avg_win_rate,
                    AVG(CASE
                        WHEN profit_factor IS NOT NULL AND profit_factor < 1e15
                        THEN profit_factor END) as avg_pf,
                    AVG(total_pnl_r) as avg_pnl_r
                FROM backtest_runs
            """).fetchone()
            total_runs = row[0] or 0
            avg_win_rate = round(row[1], 4) if row[1] is not None else None
            avg_pf = round(row[2], 4) if row[2] is not None else None
            avg_pnl_r = round(row[3], 4) if row[3] is not None else None
    except sqlite3.OperationalError:
        pass

    return JournalVsBacktest(
        journal=journal_stats,
        backtest=BacktestAggregate(
            total_runs=total_runs,
            avg_win_rate=avg_win_rate,
            avg_profit_factor=avg_pf,
            avg_total_pnl_r=avg_pnl_r,
        ),
    )
