from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd

from hps_algo.data import KiteDataConfig, filter_nse_equity_instruments
from hps_algo.kite_client import build_kite
from hps_algo.strategies.hps_algo import AboveEmaResult, KiteStrategyClient, _pct_above


@dataclass(frozen=True)
class Ema10CrossCondition:
    label: str
    crossed_references: tuple[str, ...]


class EmaPreCrossStrategy:
    name = "EMA_PRE_CROSS"

    def run(
        self,
        config: KiteDataConfig,
        kite: KiteStrategyClient | None = None,
    ) -> list[AboveEmaResult]:
        return find_kite_stocks_for_ema_pre_cross(config, kite=kite)


class EmaPreCross10Strategy:
    name = "EMA_PRE_CROSS_10"

    def run(
        self,
        config: KiteDataConfig,
        kite: KiteStrategyClient | None = None,
    ) -> list[AboveEmaResult]:
        return find_kite_stocks_for_ema_pre_cross_10(config, kite=kite)


def find_kite_stocks_for_ema_pre_cross(
    config: KiteDataConfig,
    kite: KiteStrategyClient | None = None,
    ema_period: int = 200,
) -> list[AboveEmaResult]:
    return _find_kite_stocks_for_ema_pre_cross(
        config,
        kite=kite,
        ema_period=ema_period,
        require_previous_10_alignment=False,
    )


def find_kite_stocks_for_ema_pre_cross_10(
    config: KiteDataConfig,
    kite: KiteStrategyClient | None = None,
    ema_period: int = 200,
) -> list[AboveEmaResult]:
    return _find_kite_stocks_for_ema_pre_cross(
        config,
        kite=kite,
        ema_period=ema_period,
        require_previous_10_alignment=True,
    )


def _find_kite_stocks_for_ema_pre_cross(
    config: KiteDataConfig,
    kite: KiteStrategyClient | None,
    ema_period: int,
    require_previous_10_alignment: bool,
) -> list[AboveEmaResult]:
    kite = kite or build_kite()
    instruments = kite.instruments(config.exchange)
    selected = filter_nse_equity_instruments(instruments, config)
    if config.max_symbols:
        selected = selected[: config.max_symbols]

    to_date = date.today()
    from_date = to_date - timedelta(days=max(config.history_days, ema_period * 6))
    ema_by_symbol: dict[str, dict[str, float | Ema10CrossCondition]] = {}

    for instrument in selected:
        symbol = str(instrument["tradingsymbol"])
        token = int(instrument["instrument_token"])
        candles = kite.historical_data(token, from_date, to_date, config.interval)
        closes = [float(candle["close"]) for candle in candles]
        if len(closes) < ema_period:
            continue

        data = pd.DataFrame({"close": closes})
        data["ema_10"] = data["close"].ewm(span=10, adjust=False).mean()
        data["ema_20"] = data["close"].ewm(span=20, adjust=False).mean()
        data["ema_50"] = data["close"].ewm(span=50, adjust=False).mean()
        data["ema_200"] = data["close"].ewm(span=ema_period, adjust=False).mean()
        if require_previous_10_alignment and not _previous_10_plus_ema_alignment(data):
            continue

        condition = _ema_10_cross_condition(
            data,
            reference_names=("EMA20",) if require_previous_10_alignment else ("EMA20", "EMA50"),
        )
        if not condition:
            continue

        latest = data.iloc[-1]
        ema_10 = float(latest["ema_10"])
        ema_20 = float(latest["ema_20"])
        ema_50 = float(latest["ema_50"])
        ema_200 = float(latest["ema_200"])
        if ema_10 <= ema_200 or ema_20 <= ema_200 or ema_50 <= ema_200:
            continue
        if not _ema_10_cross_distance_valid(
            ema_10,
            ema_20,
            ema_50,
            condition.crossed_references,
        ):
            continue

        condition_label = f"{condition.label}; crossed EMA distance <= 1"
        if require_previous_10_alignment:
            condition_label = (
                f"{condition.label}; previous 10+ EMA10 < EMA20 < EMA50; crossed EMA distance <= 1"
            )

        ema_by_symbol[symbol] = {
            "ema_10": ema_10,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "condition": condition_label,
        }

    if not ema_by_symbol:
        return []

    ltp_values: dict[str, dict[str, Any]] = {}
    instrument_keys = [f"{config.exchange}:{symbol}" for symbol in ema_by_symbol]
    for batch_start in range(0, len(instrument_keys), 100):
        batch = instrument_keys[batch_start : batch_start + 100]
        ltp_values.update(kite.ltp(batch))

    results: list[AboveEmaResult] = []
    for symbol, ema_values in ema_by_symbol.items():
        ltp_payload = ltp_values.get(f"{config.exchange}:{symbol}")
        if not ltp_payload:
            continue

        ltp = float(ltp_payload["last_price"])
        ema_10 = float(ema_values["ema_10"])
        ema_20 = float(ema_values["ema_20"])
        ema_50 = float(ema_values["ema_50"])
        ema_200 = float(ema_values["ema_200"])
        if ltp <= ema_200:
            continue

        above_ema_10_pct = _pct_above(ltp, ema_10)
        above_ema_20_pct = _pct_above(ltp, ema_20)
        above_ema_50_pct = _pct_above(ltp, ema_50)
        results.append(
            AboveEmaResult(
                symbol=symbol,
                ltp=round(ltp, 2),
                ema_10=round(ema_10, 2),
                ema_20=round(ema_20, 2),
                ema_50=round(ema_50, 2),
                ema_200=round(ema_200, 2),
                rsi_14=0.0,
                condition=str(ema_values["condition"]),
                entry_zone="Not Applied",
                above_ema_10_pct=round(above_ema_10_pct, 2),
                above_ema_20_pct=round(above_ema_20_pct, 2),
                above_ema_50_pct=round(above_ema_50_pct, 2),
                high_reference="Not Applied",
                high_price=0.0,
                below_high_pct=0.0,
            )
        )

    return sorted(results, key=lambda item: item.symbol)


def _ema_10_cross_condition(
    data: pd.DataFrame,
    reference_names: tuple[str, ...] = ("EMA20", "EMA50"),
) -> Ema10CrossCondition | None:
    if len(data) < 2:
        return None

    previous = data.iloc[-2]
    latest = data.iloc[-1]
    crossed: list[str] = []
    for reference_name in reference_names:
        reference_column = reference_name.lower().replace("ema", "ema_")
        if _ema_10_crossed_above(
            float(previous["ema_10"]),
            float(previous[reference_column]),
            float(latest["ema_10"]),
            float(latest[reference_column]),
        ):
            crossed.append(reference_name)

    if not crossed:
        return None

    return Ema10CrossCondition(
        label=f"EMA10 crossed above {' and '.join(crossed)}",
        crossed_references=tuple(crossed),
    )


def _previous_10_plus_ema_alignment(data: pd.DataFrame, min_candles: int = 10) -> bool:
    previous = data.iloc[:-1]
    consecutive_count = 0

    for _, candle in previous.iloc[::-1].iterrows():
        if float(candle["ema_10"]) < float(candle["ema_20"]) < float(candle["ema_50"]):
            consecutive_count += 1
            continue
        break

    return consecutive_count >= min_candles


def _ema_10_crossed_above(
    previous_ema_10: float,
    previous_reference_ema: float,
    latest_ema_10: float,
    latest_reference_ema: float,
) -> bool:
    return previous_ema_10 <= previous_reference_ema and latest_ema_10 > latest_reference_ema


def _ema_10_cross_distance_valid(
    ema_10: float,
    ema_20: float,
    ema_50: float,
    crossed_references: tuple[str, ...],
    max_distance: float = 1.0,
) -> bool:
    if "EMA20" in crossed_references and 0 < (ema_10 - ema_20) <= max_distance:
        return True
    if "EMA50" in crossed_references and 0 < (ema_10 - ema_50) <= max_distance:
        return True
    return False
