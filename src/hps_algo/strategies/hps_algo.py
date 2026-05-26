from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from hps_algo.data import KiteDataConfig, filter_nse_equity_instruments
from hps_algo.kite_client import build_kite


REQUIRED_COLUMNS = ("symbol", "date", "open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class AboveEmaResult:
    symbol: str
    ltp: float
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
        rsi_14 = float(_rsi(data["close"], 14).iloc[-1])
        if (
            close > ema_200
            and ema_10 > ema_200
            and ema_20 > ema_200
            and rsi_14 > 63
            and condition
            and entry_zone
            and high_condition
        ):
            results.append(
                AboveEmaResult(
                    symbol=str(symbol),
                    ltp=round(close, 2),
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

    to_date = date.today()
    from_date = to_date - timedelta(days=max(config.history_days, ema_period * 6))
    ema_by_symbol: dict[
        str,
        tuple[float, float, float, float, float, str, tuple[str, float, float]],
    ] = {}

    for instrument in selected:
        symbol = str(instrument["tradingsymbol"])
        token = int(instrument["instrument_token"])
        candles = kite.historical_data(token, from_date, to_date, config.interval)
        closes = [float(candle["close"]) for candle in candles]
        if len(closes) < ema_period:
            continue

        data = pd.DataFrame(
            {
                "close": closes,
                "high": [float(candle["high"]) for candle in candles],
            }
        )
        data["ema_10"] = data["close"].ewm(span=10, adjust=False).mean()
        data["ema_20"] = data["close"].ewm(span=20, adjust=False).mean()
        data["ema_50"] = data["close"].ewm(span=50, adjust=False).mean()
        data["ema_200"] = data["close"].ewm(span=ema_period, adjust=False).mean()
        data["rsi_14"] = _rsi(data["close"], 14)
        condition = _ema_10_20_condition(data)
        if not condition:
            continue

        latest = data.iloc[-1]
        rsi_14 = float(latest["rsi_14"])
        if rsi_14 <= 63:
            continue

        high_condition = _high_distance_condition(float(closes[-1]), data)
        if require_high_distance:
            if not high_condition:
                continue
        else:
            high_condition = ("Not Applied", 0.0, 0.0)

        ema_by_symbol[symbol] = (
            float(latest["ema_10"]),
            float(latest["ema_20"]),
            float(latest["ema_50"]),
            float(latest["ema_200"]),
            rsi_14,
            condition,
            high_condition,
        )

    if not ema_by_symbol:
        return []

    ltp_values: dict[str, dict[str, Any]] = {}
    instrument_keys = [f"{config.exchange}:{symbol}" for symbol in ema_by_symbol]
    for batch_start in range(0, len(instrument_keys), 100):
        batch = instrument_keys[batch_start : batch_start + 100]
        ltp_values.update(kite.ltp(batch))

    results: list[AboveEmaResult] = []
    for symbol, (
        ema_10,
        ema_20,
        ema_50,
        ema_200,
        rsi_14,
        condition,
        high_condition,
    ) in ema_by_symbol.items():
        ltp_payload = ltp_values.get(f"{config.exchange}:{symbol}")
        if not ltp_payload:
            continue
        ltp = float(ltp_payload["last_price"])
        entry_zone = _entry_zone_condition(ltp, ema_10, ema_20)
        above_ema_10_pct = _pct_above(ltp, ema_10)
        above_ema_20_pct = _pct_above(ltp, ema_20)
        above_ema_50_pct = _pct_above(ltp, ema_50)
        if ltp > ema_200 and ema_10 > ema_200 and ema_20 > ema_200 and entry_zone:
            results.append(
                AboveEmaResult(
                    symbol=symbol,
                    ltp=round(ltp, 2),
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
    max_above_pct: float = 3.0,
) -> str | None:
    matches = []
    above_ema_10_pct = _pct_above(price, ema_10)
    above_ema_20_pct = _pct_above(price, ema_20)

    if 0 < above_ema_10_pct <= max_above_pct:
        matches.append("Near EMA10")
    if 0 < above_ema_20_pct <= max_above_pct:
        matches.append("Near EMA20")

    return ", ".join(matches) if matches else None


def _pct_above(price: float, reference: float) -> float:
    return ((price - reference) / reference) * 100


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
