from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from hps_algo.data import (
    KiteDataConfig,
    fetch_kite_historical_data_cached,
    filter_nse_equity_instruments,
    save_kite_instruments_to_store,
)
from hps_algo.kite_client import build_kite
from hps_algo.strategies.hps_algo import (
    AboveEmaResult,
    KiteStrategyClient,
    MIN_LATEST_CANDLE_VOLUME,
    _completed_history_date,
    _historical_candle_frame,
    _latest_close_reference,
    _pct_above,
    _price_change_pct,
    _save_completed_indicator_snapshot,
    _with_live_close,
)


class EmaStrategy:
    name = "EMA"

    def run(
        self,
        config: KiteDataConfig,
        kite: KiteStrategyClient | None = None,
    ) -> list[AboveEmaResult]:
        return find_kite_stocks_price_above_200_ema(config, kite=kite)


def find_kite_stocks_price_above_200_ema(
    config: KiteDataConfig,
    kite: KiteStrategyClient | None = None,
    ema_period: int = 200,
) -> list[AboveEmaResult]:
    kite = kite or build_kite()
    instruments = kite.instruments(config.exchange)
    selected = filter_nse_equity_instruments(instruments, config)
    if config.max_symbols:
        selected = selected[: config.max_symbols]
    save_kite_instruments_to_store(
        selected,
        use_local_store=config.use_local_store,
        store_path=config.store_path,
    )

    to_date = _completed_history_date()
    from_date = to_date - timedelta(days=max(config.history_days, ema_period * 6))
    ema_by_symbol: dict[str, dict[str, float | int | str | pd.DataFrame]] = {}

    for instrument in selected:
        symbol = str(instrument["tradingsymbol"])
        stock_name = str(instrument.get("name") or symbol)
        token = int(instrument["instrument_token"])
        candles = fetch_kite_historical_data_cached(
            kite,
            token,
            from_date,
            to_date,
            config.interval,
            use_local_store=config.use_local_store,
            store_path=config.store_path,
        )
        closes = [float(candle["close"]) for candle in candles]
        if len(closes) < ema_period:
            continue

        history = _historical_candle_frame(candles, from_date)
        _save_completed_indicator_snapshot(
            token,
            config.interval,
            history,
            ema_period,
            use_local_store=config.use_local_store,
            store_path=config.store_path,
        )
        volume = int(candles[-1].get("volume", 0))
        if volume <= MIN_LATEST_CANDLE_VOLUME:
            continue
        ema_by_symbol[symbol] = {
            "stock_name": stock_name,
            "volume": volume,
            "latest_close": _latest_close_reference(candles),
            "history": history,
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
        live_data = _with_live_close(pd.DataFrame(ema_values["history"]), ltp)
        live_data["ema_10"] = live_data["close"].ewm(span=10, adjust=False).mean()
        live_data["ema_20"] = live_data["close"].ewm(span=20, adjust=False).mean()
        live_data["ema_50"] = live_data["close"].ewm(span=50, adjust=False).mean()
        live_data["ema_200"] = live_data["close"].ewm(span=ema_period, adjust=False).mean()
        latest = live_data.iloc[-1]
        ema_10 = float(latest["ema_10"])
        ema_20 = float(latest["ema_20"])
        ema_50 = float(latest["ema_50"])
        ema_200 = float(latest["ema_200"])
        if ltp <= ema_200 or ema_10 <= ema_200 or ema_20 <= ema_200 or ema_50 <= ema_200:
            continue
        if not _ema_10_above_20_within_distance(ema_10, ema_20):
            continue

        above_ema_10_pct = _pct_above(ltp, ema_10)
        above_ema_20_pct = _pct_above(ltp, ema_20)
        above_ema_50_pct = _pct_above(ltp, ema_50)
        entry_zone = _entry_zone_condition(
            above_ema_10_pct,
            above_ema_20_pct,
            above_ema_50_pct,
        )
        if not entry_zone:
            continue

        results.append(
            AboveEmaResult(
                symbol=symbol,
                stock_name=str(ema_values["stock_name"]),
                ltp=round(ltp, 2),
                volume=int(ema_values["volume"]),
                latest_candle_pct=round(_price_change_pct(float(ema_values["latest_close"]), ltp), 2),
                ema_10=round(ema_10, 2),
                ema_20=round(ema_20, 2),
                ema_50=round(ema_50, 2),
                ema_200=round(ema_200, 2),
                rsi_14=0.0,
                condition="Price, EMA10, EMA20, EMA50 > EMA200; EMA10 >= EMA20 within 1",
                entry_zone=entry_zone,
                above_ema_10_pct=round(above_ema_10_pct, 2),
                above_ema_20_pct=round(above_ema_20_pct, 2),
                above_ema_50_pct=round(above_ema_50_pct, 2),
                high_reference="Not Applied",
                high_price=0.0,
                below_high_pct=0.0,
            )
        )

    return sorted(results, key=lambda item: item.symbol)


def _ema_10_above_20_within_distance(
    ema_10: float,
    ema_20: float,
    max_distance: float = 1.0,
) -> bool:
    return ema_10 >= ema_20 and (ema_10 - ema_20) <= max_distance


def _entry_zone_condition(
    above_ema_10_pct: float,
    above_ema_20_pct: float,
    above_ema_50_pct: float,
    max_above_pct: float = 1.5,
) -> str | None:
    if (
        0 <= above_ema_10_pct <= max_above_pct
        and 0 <= above_ema_20_pct <= max_above_pct
        and 0 <= above_ema_50_pct <= max_above_pct
    ):
        return "Within 1.5% of EMA10, EMA20, EMA50"

    return None
