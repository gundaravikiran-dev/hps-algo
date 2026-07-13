from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from hps_algo.runtime_paths import state_root


def default_market_data_path() -> Path:
    return state_root() / "data" / "market_data.sqlite3"


class MarketDataStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_market_data_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def has_synced_range(
        self,
        instrument_token: int,
        interval: str,
        from_date: date,
        to_date: date,
    ) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM candle_sync_ranges
                WHERE instrument_token = ?
                  AND interval = ?
                  AND from_date <= ?
                  AND to_date >= ?
                LIMIT 1
                """,
                (instrument_token, interval, from_date.isoformat(), to_date.isoformat()),
            ).fetchone()
        return row is not None

    def load_candles(
        self,
        instrument_token: int,
        interval: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT candle_date, open, high, low, close, volume
                FROM candles
                WHERE instrument_token = ?
                  AND interval = ?
                  AND substr(candle_date, 1, 10) BETWEEN ? AND ?
                ORDER BY candle_date
                """,
                (instrument_token, interval, from_date.isoformat(), to_date.isoformat()),
            ).fetchall()

        candles_by_date: dict[date, dict[str, Any]] = {}
        for row in rows:
            candle_date = _date_from_value(row["candle_date"])
            candles_by_date[candle_date] = {
                "date": candle_date,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            }

        return [candles_by_date[candle_date] for candle_date in sorted(candles_by_date)]

    def save_candles(
        self,
        instrument_token: int,
        interval: str,
        candles: list[dict[str, Any]],
    ) -> None:
        if not candles:
            return

        rows = [
            (
                instrument_token,
                interval,
                _date_to_iso(candle["date"]),
                float(candle.get("open", 0)),
                float(candle.get("high", 0)),
                float(candle.get("low", 0)),
                float(candle.get("close", 0)),
                int(candle.get("volume", 0)),
            )
            for candle in candles
        ]

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO candles (
                    instrument_token,
                    interval,
                    candle_date,
                    open,
                    high,
                    low,
                    close,
                    volume
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(instrument_token, interval, candle_date) DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume
                """,
                rows,
            )

    def mark_synced_range(
        self,
        instrument_token: int,
        interval: str,
        from_date: date,
        to_date: date,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO candle_sync_ranges (
                    instrument_token,
                    interval,
                    from_date,
                    to_date,
                    updated_at
                )
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (instrument_token, interval, from_date.isoformat(), to_date.isoformat()),
            )

    def save_instruments(self, instruments: list[dict[str, Any]]) -> None:
        if not instruments:
            return

        rows = [
            (
                int(instrument["instrument_token"]),
                str(instrument.get("exchange", "")),
                str(instrument.get("segment", "")),
                str(instrument.get("instrument_type", "")),
                str(instrument.get("tradingsymbol", "")),
                str(instrument.get("name", "")),
            )
            for instrument in instruments
            if instrument.get("instrument_token")
        ]

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO instruments (
                    instrument_token,
                    exchange,
                    segment,
                    instrument_type,
                    tradingsymbol,
                    stock_name,
                    last_updated
                )
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(instrument_token) DO UPDATE SET
                    exchange = excluded.exchange,
                    segment = excluded.segment,
                    instrument_type = excluded.instrument_type,
                    tradingsymbol = excluded.tradingsymbol,
                    stock_name = excluded.stock_name,
                    last_updated = excluded.last_updated
                """,
                rows,
            )

    def save_technical_indicator(
        self,
        instrument_token: int,
        interval: str,
        candle_date: date,
        ema_10: float,
        ema_20: float,
        ema_50: float,
        ema_200: float,
        rsi_14: float,
        high_52w: float,
        all_time_high: float,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO technical_indicators (
                    instrument_token,
                    interval,
                    candle_date,
                    ema_10,
                    ema_20,
                    ema_50,
                    ema_200,
                    rsi_14,
                    high_52w,
                    all_time_high,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(instrument_token, interval, candle_date) DO UPDATE SET
                    ema_10 = excluded.ema_10,
                    ema_20 = excluded.ema_20,
                    ema_50 = excluded.ema_50,
                    ema_200 = excluded.ema_200,
                    rsi_14 = excluded.rsi_14,
                    high_52w = excluded.high_52w,
                    all_time_high = excluded.all_time_high,
                    updated_at = excluded.updated_at
                """,
                (
                    instrument_token,
                    interval,
                    candle_date.isoformat(),
                    ema_10,
                    ema_20,
                    ema_50,
                    ema_200,
                    rsi_14,
                    high_52w,
                    all_time_high,
                ),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS candles (
                    instrument_token INTEGER NOT NULL,
                    interval TEXT NOT NULL,
                    candle_date TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    PRIMARY KEY (instrument_token, interval, candle_date)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS candle_sync_ranges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instrument_token INTEGER NOT NULL,
                    interval TEXT NOT NULL,
                    from_date TEXT NOT NULL,
                    to_date TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS instruments (
                    instrument_token INTEGER PRIMARY KEY,
                    exchange TEXT NOT NULL,
                    segment TEXT NOT NULL,
                    instrument_type TEXT NOT NULL,
                    tradingsymbol TEXT NOT NULL,
                    stock_name TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_instruments_symbol
                ON instruments (exchange, tradingsymbol)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS technical_indicators (
                    instrument_token INTEGER NOT NULL,
                    interval TEXT NOT NULL,
                    candle_date TEXT NOT NULL,
                    ema_10 REAL NOT NULL,
                    ema_20 REAL NOT NULL,
                    ema_50 REAL NOT NULL,
                    ema_200 REAL NOT NULL,
                    rsi_14 REAL NOT NULL,
                    high_52w REAL NOT NULL,
                    all_time_high REAL NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (instrument_token, interval, candle_date)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_technical_indicators_latest
                ON technical_indicators (instrument_token, interval, candle_date)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_candle_sync_ranges_lookup
                ON candle_sync_ranges (
                    instrument_token,
                    interval,
                    from_date,
                    to_date
                )
                """
            )


def _date_to_iso(value: Any) -> str:
    return _date_from_value(value).isoformat()


def _date_from_value(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "date"):
        return value.date()
    return date.fromisoformat(str(value)[:10])
