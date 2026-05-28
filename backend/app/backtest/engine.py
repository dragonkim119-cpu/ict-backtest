from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.backtest.entry import find_entry_signal
from app.backtest.metrics import compute_metrics
from app.backtest.mtf_entry import is_within_htf_bpr
from app.backtest.simulate import simulate_trade
from app.backtest.stop import calc_stop_loss, calc_take_profit
from app.models.patterns import BPR, KillZoneSpan, Sweep, Swing
from app.models.trade import Metrics, Trade


def _db_path() -> Path:
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "backtest.db"


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS backtest_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT UNIQUE NOT NULL,
            symbol TEXT NOT NULL,
            interval TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            params_hash TEXT NOT NULL,
            params_json TEXT NOT NULL,
            total_trades INTEGER,
            wins INTEGER,
            losses INTEGER,
            timeouts INTEGER,
            win_rate REAL,
            profit_factor REAL,
            expectancy REAL,
            total_pnl_r REAL,
            max_drawdown_r REAL,
            max_consecutive_losses INTEGER,
            avg_trade_duration_candles REAL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS backtest_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            entry_index INTEGER,
            entry_time TEXT,
            entry_price REAL,
            direction TEXT,
            sl REAL,
            tp REAL,
            exit_index INTEGER,
            exit_time TEXT,
            exit_price REAL,
            status TEXT,
            pnl_r REAL,
            FOREIGN KEY (run_id) REFERENCES backtest_runs(run_id)
        );
    """)
    conn.commit()


def _params_hash(
    symbol: str,
    interval: str,
    start: str | None,
    end: str | None,
    kill_zone_only: bool,
    require_sweep: bool,
    htf_interval: str | None = None,
) -> str:
    payload = json.dumps(
        {
            "symbol": symbol,
            "interval": interval,
            "start": start,
            "end": end,
            "kill_zone_only": kill_zone_only,
            "require_sweep": require_sweep,
            "htf_interval": htf_interval,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _in_kill_zone(entry_time: datetime, kill_zones: list[KillZoneSpan]) -> bool:
    for kz in kill_zones:
        if kz.start_time <= entry_time <= kz.end_time:
            return True
    return False


def _has_recent_sweep(bpr: BPR, sweeps: list[Sweep], lookback: int = 50) -> bool:
    for s in sweeps:
        if bpr.created_index - lookback <= s.sweep_index <= bpr.created_index:
            return True
    return False


def _run_id(params_hash: str) -> str:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    return f"{ts}_{params_hash}"


def run_backtest(
    symbol: str,
    interval: str,
    candles: pd.DataFrame,
    bprs: list[BPR],
    swings: list[Swing],
    start: str | None = None,
    end: str | None = None,
    kill_zone_only: bool = False,
    kill_zones: list[KillZoneSpan] | None = None,
    require_sweep: bool = False,
    sweeps: list[Sweep] | None = None,
    htf_interval: str | None = None,
    htf_bprs: list[BPR] | None = None,
) -> tuple[str, list[Trade], Metrics]:
    """Execute BPR backtest. Returns (run_id, trades, metrics)."""
    trades: list[Trade] = []
    _kill_zones = kill_zones or []
    _sweeps = sweeps or []

    for bpr in bprs:
        if require_sweep and not _has_recent_sweep(bpr, _sweeps):
            continue

        signal = find_entry_signal(bpr, candles)
        if signal is None:
            continue

        if kill_zone_only and not _in_kill_zone(signal.entry_time, _kill_zones):
            continue

        if htf_bprs and not is_within_htf_bpr(signal.entry_price, signal.entry_time, htf_bprs):
            continue

        sl = calc_stop_loss(signal, swings)
        if sl is None:
            continue

        tp = calc_take_profit(signal.entry_price, sl, signal.direction)
        trade = simulate_trade(signal, sl, tp, candles)
        trades.append(trade)

    metrics = compute_metrics(trades)
    params_hash = _params_hash(symbol, interval, start, end, kill_zone_only, require_sweep, htf_interval)
    run_id = _run_id(params_hash)

    _save_results(run_id, symbol, interval, start, end, params_hash, trades, metrics, htf_interval)
    return run_id, trades, metrics


def _save_results(
    run_id: str,
    symbol: str,
    interval: str,
    start: str | None,
    end: str | None,
    params_hash: str,
    trades: list[Trade],
    metrics: Metrics,
    htf_interval: str | None = None,
) -> None:
    params_json = json.dumps(
        {"symbol": symbol, "interval": interval, "start": start, "end": end, "htf_interval": htf_interval}
    )
    now = datetime.utcnow().isoformat()

    with sqlite3.connect(_db_path()) as conn:
        _ensure_tables(conn)
        conn.execute(
            """INSERT OR REPLACE INTO backtest_runs
               (run_id, symbol, interval, start_time, end_time, params_hash, params_json,
                total_trades, wins, losses, timeouts, win_rate, profit_factor, expectancy,
                total_pnl_r, max_drawdown_r, max_consecutive_losses, avg_trade_duration_candles,
                created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, symbol, interval, start, end, params_hash, params_json,
                metrics.total_trades, metrics.wins, metrics.losses, metrics.timeouts,
                metrics.win_rate, metrics.profit_factor, metrics.expectancy,
                metrics.total_pnl_r, metrics.max_drawdown_r, metrics.max_consecutive_losses,
                metrics.avg_trade_duration_candles, now,
            ),
        )
        for t in trades:
            conn.execute(
                """INSERT INTO backtest_trades
                   (run_id, entry_index, entry_time, entry_price, direction,
                    sl, tp, exit_index, exit_time, exit_price, status, pnl_r)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    t.entry.entry_index,
                    t.entry.entry_time.isoformat(),
                    t.entry.entry_price,
                    t.entry.direction,
                    t.sl, t.tp,
                    t.exit_index,
                    t.exit_time.isoformat(),
                    t.exit_price,
                    t.status,
                    t.pnl_r,
                ),
            )
        conn.commit()


# ── query helpers ──────────────────────────────────────────────────


_RUN_COLS = (
    "run_id", "symbol", "interval", "start_time", "end_time",
    "params_hash", "params_json", "total_trades", "wins", "losses", "timeouts",
    "win_rate", "profit_factor", "expectancy", "total_pnl_r",
    "max_drawdown_r", "max_consecutive_losses", "avg_trade_duration_candles", "created_at",
)

_TRADE_COLS = (
    "entry_index", "entry_time", "entry_price", "direction",
    "sl", "tp", "exit_index", "exit_time", "exit_price", "status", "pnl_r",
)


def _row_to_dict(row: tuple, cols: tuple) -> dict:
    d = dict(zip(cols, row))
    # Replace Python inf with a sentinel the JSON encoder can handle
    for k, v in d.items():
        if isinstance(v, float) and (v != v or v == float("inf") or v == float("-inf")):
            d[k] = None
    return d


def list_runs(limit: int = 50) -> list[dict]:
    db = _db_path()
    if not db.exists():
        return []
    with sqlite3.connect(db) as conn:
        _ensure_tables(conn)
        cols_sql = ", ".join(_RUN_COLS)
        rows = conn.execute(
            f"SELECT {cols_sql} FROM backtest_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_dict(r, _RUN_COLS) for r in rows]


def get_run_detail(run_id: str) -> tuple[dict, list[dict]] | None:
    db = _db_path()
    if not db.exists():
        return None
    with sqlite3.connect(db) as conn:
        _ensure_tables(conn)
        run_cols_sql = ", ".join(_RUN_COLS)
        run_row = conn.execute(
            f"SELECT {run_cols_sql} FROM backtest_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if run_row is None:
            return None
        trade_cols_sql = ", ".join(_TRADE_COLS)
        trade_rows = conn.execute(
            f"SELECT {trade_cols_sql} FROM backtest_trades WHERE run_id = ? ORDER BY entry_index",
            (run_id,),
        ).fetchall()
    run_dict = _row_to_dict(run_row, _RUN_COLS)
    trades_list = [_row_to_dict(r, _TRADE_COLS) for r in trade_rows]
    return run_dict, trades_list
