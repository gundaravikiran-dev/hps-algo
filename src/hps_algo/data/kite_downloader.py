from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
import yaml

from hps_algo.kite_client import build_kite


@dataclass(frozen=True)
class KiteDataConfig:
    exchange: str = "NSE"
    interval: str = "day"
    history_days: int = 420
    output_path: str = "data/nse_daily_candles.csv"
    max_symbols: int | None = 50
    pause_seconds: float = 0.35
    exclude_tradingsymbol_suffixes: tuple[str, ...] = (
        "-BE",
        "-BZ",
        "-SM",
        "-ST",
        "-SZ",
        "-GB",
        "-GS",
    )
    exclude_symbol_contains: tuple[str, ...] = ("-",)
    exclude_name_contains: tuple[str, ...] = ("ETF", "INAV", "BEES", "GILT")


@dataclass(frozen=True)
class DownloadSummary:
    output_path: str
    instruments_seen: int
    instruments_selected: int
    symbols_downloaded: int
    rows_written: int
    selected_symbols: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KiteHistoryClient(Protocol):
    def instruments(self, exchange: str) -> list[dict[str, Any]]:
        """Return Kite instruments for the exchange."""

    def historical_data(
        self,
        instrument_token: int,
        from_date: date,
        to_date: date,
        interval: str,
    ) -> list[dict[str, Any]]:
        """Return historical candles."""


def load_kite_data_config(path: str | Path = "config/data.yaml") -> KiteDataConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    config = raw.get("kite_data", raw)
    if "exclude_tradingsymbol_suffixes" in config:
        config["exclude_tradingsymbol_suffixes"] = tuple(config["exclude_tradingsymbol_suffixes"])
    if "exclude_symbol_contains" in config:
        config["exclude_symbol_contains"] = tuple(config["exclude_symbol_contains"])
    if "exclude_name_contains" in config:
        config["exclude_name_contains"] = tuple(config["exclude_name_contains"])
    return KiteDataConfig(**config)


def filter_nse_equity_instruments(
    instruments: list[dict[str, Any]],
    config: KiteDataConfig,
) -> list[dict[str, Any]]:
    selected = []
    suffixes = tuple(config.exclude_tradingsymbol_suffixes)

    for instrument in instruments:
        tradingsymbol = str(instrument.get("tradingsymbol", "")).strip()
        name = str(instrument.get("name", "")).strip()
        if not tradingsymbol:
            continue
        if not name:
            continue
        if instrument.get("exchange") != config.exchange:
            continue
        if instrument.get("segment") != config.exchange:
            continue
        if instrument.get("instrument_type") != "EQ":
            continue
        if tradingsymbol.endswith(suffixes):
            continue
        if any(value in tradingsymbol for value in config.exclude_symbol_contains):
            continue
        if any(value.upper() in name.upper() for value in config.exclude_name_contains):
            continue
        selected.append(instrument)

    return sorted(selected, key=lambda item: str(item["tradingsymbol"]))


def download_nse_daily_candles(
    config: KiteDataConfig,
    kite: KiteHistoryClient | None = None,
) -> DownloadSummary:
    kite = kite or build_kite()
    output_path = Path(config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    instruments = kite.instruments(config.exchange)
    selected = filter_nse_equity_instruments(instruments, config)
    if config.max_symbols:
        selected = selected[: config.max_symbols]

    to_date = date.today()
    from_date = to_date - timedelta(days=config.history_days)
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for instrument in selected:
        symbol = str(instrument["tradingsymbol"])
        token = int(instrument["instrument_token"])
        try:
            candles = kite.historical_data(token, from_date, to_date, config.interval)
        except Exception as error:
            errors.append(f"{symbol}: {error}")
            continue

        for candle in candles:
            rows.append(
                {
                    "symbol": symbol,
                    "date": candle["date"],
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle["volume"],
                }
            )

        if config.pause_seconds:
            time.sleep(config.pause_seconds)

    data = pd.DataFrame(rows, columns=["symbol", "date", "open", "high", "low", "close", "volume"])
    if not data.empty:
        data["date"] = pd.to_datetime(data["date"]).dt.date
    data.to_csv(output_path, index=False)

    return DownloadSummary(
        output_path=str(output_path),
        instruments_seen=len(instruments),
        instruments_selected=len(selected),
        symbols_downloaded=data["symbol"].nunique() if not data.empty else 0,
        rows_written=len(data),
        selected_symbols=[str(item["tradingsymbol"]) for item in selected],
        errors=errors,
    )
