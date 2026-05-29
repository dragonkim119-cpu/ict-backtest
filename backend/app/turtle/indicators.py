from __future__ import annotations

import pandas as pd


def _donchian_high(df: pd.DataFrame, period: int) -> pd.Series:
    return df["high"].shift(1).rolling(period).max()


def _donchian_low(df: pd.DataFrame, period: int) -> pd.Series:
    return df["low"].shift(1).rolling(period).min()


def compute_donchian(df: pd.DataFrame) -> pd.DataFrame:
    """Compute System1 (20/10) and System2 (55/20) Donchian channels.

    All channel values are based on the PREVIOUS candle (shift(1)) so that
    signals fire when price crosses the channel on the current candle's close.

    Columns added:
      s1_upper, s1_lower  — 20-day high / 10-day low
      s2_upper, s2_lower  — 55-day high / 20-day low
      s1_entry_long, s1_entry_short, s1_exit_long, s1_exit_short
      s2_entry_long, s2_entry_short, s2_exit_long, s2_exit_short
    """
    df = df.copy()

    df["s1_upper"] = _donchian_high(df, 20)
    df["s1_lower"] = _donchian_low(df, 10)
    df["s2_upper"] = _donchian_high(df, 55)
    df["s2_lower"] = _donchian_low(df, 20)

    close = df["close"]

    df["s1_entry_long"] = close > df["s1_upper"]
    df["s1_entry_short"] = close < _donchian_low(df, 20)
    df["s1_exit_long"] = close < df["s1_lower"]
    df["s1_exit_short"] = close > _donchian_high(df, 10)

    df["s2_entry_long"] = close > df["s2_upper"]
    df["s2_entry_short"] = close < df["s2_lower"]
    df["s2_exit_long"] = close < df["s2_lower"]
    df["s2_exit_short"] = close > df["s2_upper"]

    return df


def extract_signals(df: pd.DataFrame) -> list[dict]:
    """Return list of {time, system, type} signal events."""
    signals: list[dict] = []

    signal_cols = [
        ("s1_entry_long",  1, "entry_long"),
        ("s1_entry_short", 1, "entry_short"),
        ("s1_exit_long",   1, "exit_long"),
        ("s1_exit_short",  1, "exit_short"),
        ("s2_entry_long",  2, "entry_long"),
        ("s2_entry_short", 2, "entry_short"),
        ("s2_exit_long",   2, "exit_long"),
        ("s2_exit_short",  2, "exit_short"),
    ]

    for col, system, sig_type in signal_cols:
        if col not in df.columns:
            continue
        fired = df[df[col] == True]  # noqa: E712
        for _, row in fired.iterrows():
            ts = row["open_time"]
            if hasattr(ts, "isoformat"):
                t = ts.isoformat()
            else:
                t = str(ts)[:19] + "Z"
            signals.append({"time": t, "system": system, "type": sig_type})

    signals.sort(key=lambda x: x["time"])
    return signals
