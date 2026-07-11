from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from hps_algo.data import (
    KiteDataConfig,
    fetch_kite_historical_data_cached,
    filter_nse_equity_instruments,
    save_kite_instruments_to_store,
    save_technical_indicator_to_store,
)
from hps_algo.kite_client import build_kite


REQUIRED_COLUMNS = ("symbol", "date", "open", "high", "low", "close", "volume")
RSI_THRESHOLD = 60.0
MIN_LATEST_CANDLE_VOLUME = 1_000_000


@dataclass(frozen=True)
class AboveEmaResult:
    symbol: str
    stock_name: str
    ltp: float
    volume: int
    latest_candle_pct: float
    ema_10: float
    ema_20: float
    ema_50: float
    ema_200: float
    rsi_14: float
    condition: str
    entry_zone: str
    above_ema_10_pct: float
    above_ema_20_pct: float
    above_ema_50_pct: float
    high_reference: str
    high_price: float
    below_high_pct: float

    def to_dict(self) -> dict:
        return asdict(self)


class KiteStrategyClient(Protocol):
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

    def ltp(self, instruments: list[str]) -> dict[str, dict[str, Any]]:
        """Return latest traded prices."""


def find_stocks_above_200_ema(path: str | Path, ema_period: int = 200) -> list[AboveEmaResult]:
    candles = pd.read_csv(Path(path), parse_dates=["date"])
    missing = set(REQUIRED_COLUMNS).difference(candles.columns)
    if missing:
        raise ValueError(f"Missing candle columns: {sorted(missing)}")

    results: list[AboveEmaResult] = []
    for symbol, group in candles.groupby("symbol", sort=True):
        data = group.sort_values("date").copy()
        if len(data) < ema_period:
            continue

        data["ema_200"] = data["close"].ewm(span=ema_period, adjust=False).mean()
        data["ema_10"] = data["close"].ewm(span=10, adjust=False).mean()
        data["ema_20"] = data["close"].ewm(span=20, adjust=False).mean()
        data["ema_50"] = data["close"].ewm(span=50, adjust=False).mean()
        latest = data.iloc[-1]
        close = float(latest["close"])
        ema_10 = float(latest["ema_10"])
        ema_20 = float(latest["ema_20"])
        ema_50 = float(latest["ema_50"])
        ema_200 = float(latest["ema_200"])

        condition = _ema_10_20_condition(data)
        entry_zone = _entry_zone_condition(close, ema_10, ema_20)
        above_ema_10_pct = _pct_above(close, ema_10)
        above_ema_20_pct = _pct_above(close, ema_20)
        above_ema_50_pct = _pct_above(close, ema_50)
        high_condition = _high_distance_condition(close, data)
        volume = int(latest["volume"])
        rsi_14 = float(_rsi(data["close"], 14).iloc[-1])
        if (
            close > ema_200
            and ema_10 > ema_200
            and ema_20 > ema_200
            and volume > MIN_LATEST_CANDLE_VOLUME
            and rsi_14 > RSI_THRESHOLD
            and condition
            and entry_zone
            and high_condition
        ):
            results.append(
                AboveEmaResult(
                    symbol=str(symbol),
                    stock_name=str(symbol),
                    ltp=round(close, 2),
                    volume=volume,
                    latest_candle_pct=round(_price_change_pct(float(data.iloc[-2]["close"]), close), 2),
                    ema_10=round(ema_10, 2),
                    ema_20=round(ema_20, 2),
                    ema_50=round(ema_50, 2),
                    ema_200=round(ema_200, 2),
                    rsi_14=round(rsi_14, 2),
                    condition=condition,
                    entry_zone=entry_zone,
                    above_ema_10_pct=round(above_ema_10_pct, 2),
                    above_ema_20_pct=round(above_ema_20_pct, 2),
                    above_ema_50_pct=round(above_ema_50_pct, 2),
                    high_reference=high_condition[0],
                    high_price=round(high_condition[1], 2),
                    below_high_pct=round(high_condition[2], 2),
                )
            )

    return sorted(results, key=lambda item: item.symbol)


def find_kite_stocks_ltp_above_200_ema(
    config: KiteDataConfig,
    kite: KiteStrategyClient | None = None,
    ema_period: int = 200,
    require_high_distance: bool = True,
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
    history_by_symbol: dict[str, tuple[str, int, float, pd.DataFrame]] = {}

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

        data = _historical_candle_frame(candles, from_date)
        _save_completed_indicator_snapshot(
            token,
            config.interval,
            data,
            ema_period,
            use_local_store=config.use_local_store,
            store_path=config.store_path,
        )
        volume = int(candles[-1].get("volume", 0))
        if volume <= MIN_LATEST_CANDLE_VOLUME:
            continue
        history_by_symbol[symbol] = (
            stock_name,
            volume,
            _latest_close_reference(candles),
            data,
        )

    if not history_by_symbol:
        return []

    ltp_values: dict[str, dict[str, Any]] = {}
    instrument_keys = [f"{config.exchange}:{symbol}" for symbol in history_by_symbol]
    for batch_start in range(0, len(instrument_keys), 100):
        batch = instrument_keys[batch_start : batch_start + 100]
        ltp_values.update(kite.ltp(batch))

    results: list[AboveEmaResult] = []
    for symbol, (
        stock_name,
        volume,
        latest_candle_pct,
        data,
    ) in history_by_symbol.items():
        ltp_payload = ltp_values.get(f"{config.exchange}:{symbol}")
        if not ltp_payload:
            continue
        ltp = float(ltp_payload["last_price"])
        live_data = _with_live_close(data, ltp)
        live_data["ema_10"] = live_data["close"].ewm(span=10, adjust=False).mean()
        live_data["ema_20"] = live_data["close"].ewm(span=20, adjust=False).mean()
        live_data["ema_50"] = live_data["close"].ewm(span=50, adjust=False).mean()
        live_data["ema_200"] = live_data["close"].ewm(span=ema_period, adjust=False).mean()
        live_data["rsi_14"] = _rsi(live_data["close"], 14)
        condition = _ema_10_20_condition(live_data)
        if not condition:
            continue

        latest = live_data.iloc[-1]
        ema_10 = float(latest["ema_10"])
        ema_20 = float(latest["ema_20"])
        ema_50 = float(latest["ema_50"])
        ema_200 = float(latest["ema_200"])
        rsi_14 = float(latest["rsi_14"])
        if rsi_14 <= RSI_THRESHOLD:
            continue

        latest_change_pct = _price_change_pct(latest_candle_pct, ltp)
        entry_zone = _entry_zone_condition(ltp, ema_10, ema_20)
        above_ema_10_pct = _pct_above(ltp, ema_10)
        above_ema_20_pct = _pct_above(ltp, ema_20)
        above_ema_50_pct = _pct_above(ltp, ema_50)
        high_condition = _high_distance_condition(ltp, live_data)
        if require_high_distance:
            if not high_condition:
                continue
        else:
            high_condition = ("Not Applied", 0.0, 0.0)
        if _price_and_short_emas_are_above_trend(ltp, ema_10, ema_20, ema_200) and entry_zone:
            results.append(
                AboveEmaResult(
                    symbol=symbol,
                    stock_name=stock_name,
                    ltp=round(ltp, 2),
                    volume=volume,
                    latest_candle_pct=round(latest_change_pct, 2),
                    ema_10=round(ema_10, 2),
                    ema_20=round(ema_20, 2),
                    ema_50=round(ema_50, 2),
                    ema_200=round(ema_200, 2),
                    rsi_14=round(rsi_14, 2),
                    condition=condition,
                    entry_zone=entry_zone,
                    above_ema_10_pct=round(above_ema_10_pct, 2),
                    above_ema_20_pct=round(above_ema_20_pct, 2),
                    above_ema_50_pct=round(above_ema_50_pct, 2),
                    high_reference=high_condition[0],
                    high_price=round(high_condition[1], 2),
                    below_high_pct=round(high_condition[2], 2),
                )
            )

    return sorted(results, key=lambda item: item.symbol)


def _ema_10_20_condition(data: pd.DataFrame) -> str | None:
    if len(data) < 21:
        return None

    previous = data.iloc[-2]
    latest = data.iloc[-1]
    if float(latest["ema_10"]) > float(latest["ema_20"]):
        return "EMA10 > EMA20"

    if (
        float(previous["ema_10"]) <= float(previous["ema_20"])
        and float(latest["ema_10"]) > float(latest["ema_20"])
    ):
        return "EMA10 crossed EMA20"

    return None


def _entry_zone_condition(
    price: float,
    ema_10: float,
    ema_20: float,
    min_above_pct: float = 0.0,
    max_above_pct: float = 3.0,
) -> str | None:
    matches = []
    above_ema_10_pct = _pct_above(price, ema_10)
    above_ema_20_pct = _pct_above(price, ema_20)

    if min_above_pct <= above_ema_10_pct <= max_above_pct:
        matches.append("Near EMA10")
    if min_above_pct <= above_ema_20_pct <= max_above_pct:
        matches.append("Near EMA20")

    return ", ".join(matches) if matches else None


def _pct_above(price: float, reference: float) -> float:
    return ((price - reference) / reference) * 100


def _price_and_short_emas_are_above_trend(
    price: float,
    ema_10: float,
    ema_20: float,
    ema_200: float,
) -> bool:
    return (
        price > ema_200
        and (price > ema_10 or price > ema_20)
        and ema_10 > ema_200
        and ema_20 > ema_200
    )


def _with_live_close(data: pd.DataFrame, ltp: float) -> pd.DataFrame:
    live_data = data.copy()
    live_data.loc[len(live_data)] = {
        "date": date.today(),
        "close": ltp,
        "high": max(ltp, float(data["high"].iloc[-1]) if "high" in data.columns and not data.empty else ltp),
    }
    return live_data


def _historical_candle_frame(candles: list[dict[str, Any]], start_date: date) -> pd.DataFrame:
    rows = []
    for index, candle in enumerate(candles):
        candle_date = _candle_date(candle.get("date")) or start_date + timedelta(days=index)
        close = float(candle["close"])
        rows.append(
            {
                "date": candle_date,
                "close": close,
                "high": float(candle.get("high", close)),
            }
        )
    return pd.DataFrame(rows)


def _save_completed_indicator_snapshot(
    instrument_token: int,
    interval: str,
    data: pd.DataFrame,
    ema_period: int,
    use_local_store: bool,
    store_path: str | None,
) -> None:
    if data.empty:
        return

    indicators = data.copy()
    indicators["ema_10"] = indicators["close"].ewm(span=10, adjust=False).mean()
    indicators["ema_20"] = indicators["close"].ewm(span=20, adjust=False).mean()
    indicators["ema_50"] = indicators["close"].ewm(span=50, adjust=False).mean()
    indicators["ema_200"] = indicators["close"].ewm(span=ema_period, adjust=False).mean()
    indicators["rsi_14"] = _rsi(indicators["close"], 14)
    latest = indicators.iloc[-1]

    save_technical_indicator_to_store(
        instrument_token,
        interval,
        _candle_date(latest["date"]) or _completed_history_date(),
        float(latest["ema_10"]),
        float(latest["ema_20"]),
        float(latest["ema_50"]),
        float(latest["ema_200"]),
        float(latest["rsi_14"]),
        float(indicators["high"].tail(252).max()),
        float(indicators["high"].max()),
        use_local_store=use_local_store,
        store_path=store_path,
    )


def _price_change_pct(reference_price: float, price: float) -> float:
    if reference_price == 0:
        return 0.0
    return ((price - reference_price) / reference_price) * 100


def _completed_history_date() -> date:
    return date.today() - timedelta(days=1)


def _latest_close_reference(candles: list[dict[str, Any]]) -> float:
    if not candles:
        return 0.0

    latest_date = _candle_date(candles[-1].get("date"))
    if latest_date == date.today() and len(candles) > 1:
        return float(candles[-2].get("close", 0))

    return float(candles[-1].get("close", 0))


def _candle_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if hasattr(value, "date"):
        return value.date()
    try:
        return pd.Timestamp(value).date()
    except Exception:
        return None


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    relative_strength = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + relative_strength))
    return rsi.mask((avg_loss == 0) & (avg_gain > 0), 100).fillna(0)


def _high_distance_condition(
    price: float,
    data: pd.DataFrame,
    min_below_pct: float = 10.0,
    max_below_pct: float = 20.0,
) -> tuple[str, float, float] | None:
    high_column = "high" if "high" in data.columns else "close"
    high_52w = float(data[high_column].tail(252).max())
    all_time_high = float(data[high_column].max())

    candidates = (
        ("52W High", high_52w),
        ("All Time High", all_time_high),
    )
    for label, high_price in candidates:
        if high_price <= 0:
            continue
        below_high_pct = ((high_price - price) / high_price) * 100
        if min_below_pct <= below_high_pct <= max_below_pct:
            return label, high_price, below_high_pct

    return None
