from pathlib import Path
from datetime import date, timedelta

from hps_algo.data import KiteDataConfig
from hps_algo.strategies.hps_algo import (
    find_kite_stocks_ltp_above_200_ema,
    find_stocks_above_200_ema,
)


class FakeKite:
    def instruments(self, exchange: str) -> list[dict]:
        return [
            {
                "exchange": exchange,
                "segment": exchange,
                "instrument_type": "EQ",
                "tradingsymbol": "AAA",
                "name": "AAA LIMITED",
                "instrument_token": 1,
            },
            {
                "exchange": exchange,
                "segment": exchange,
                "instrument_type": "EQ",
                "tradingsymbol": "BBB",
                "name": "BBB LIMITED",
                "instrument_token": 2,
            },
        ]

    def historical_data(self, instrument_token, from_date, to_date, interval) -> list[dict]:
        if instrument_token == 1:
            return [
                {
                    "close": 100 + index,
                    "high": 370 if index == 180 else 100 + index,
                    "volume": 1_500_000,
                }
                for index in range(230)
            ]
        return [
            {"close": 300 - index, "high": 300 - index, "volume": 1_500_000}
            for index in range(230)
        ]

    def ltp(self, instruments: list[str]) -> dict:
        return {
            "NSE:AAA": {"last_price": 326},
            "NSE:BBB": {"last_price": 80},
        }


def test_find_stocks_above_200_ema(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    rows = ["symbol,date,open,high,low,close,volume"]
    start = date(2025, 1, 1)
    for index in range(210):
        day = (start + timedelta(days=index)).isoformat()
        aaa_close = 158 + (index * 0.8)
        aaa_high = 370 if index == 180 else aaa_close
        rows.append(f"AAA,{day},100,{aaa_high},90,{aaa_close},1500000")
        rows.append(f"BBB,{day},100,{300 - index},90,{300 - index},1500000")
    csv_path.write_text("\n".join(rows), encoding="utf-8")

    results = find_stocks_above_200_ema(csv_path)

    assert [item.symbol for item in results] == ["AAA"]
    assert results[0].condition == "EMA10 > EMA20"
    assert results[0].high_reference == "52W High"
    assert results[0].rsi_14 > 60


def test_find_kite_stocks_ltp_above_200_ema() -> None:
    config = KiteDataConfig(max_symbols=2, pause_seconds=0)

    results = find_kite_stocks_ltp_above_200_ema(config, kite=FakeKite())

    assert [item.symbol for item in results] == ["AAA"]
    assert results[0].ltp == 326
    assert results[0].condition == "EMA10 > EMA20"
    assert results[0].entry_zone == "Near EMA10, Near EMA20"
    assert results[0].high_reference == "52W High"
    assert results[0].rsi_14 > 60


def test_find_kite_stocks_uses_ltp_for_high_distance_filter() -> None:
    class LtpTooCloseToHighKite(FakeKite):
        def ltp(self, instruments: list[str]) -> dict:
            return {
                "NSE:AAA": {"last_price": 334},
                "NSE:BBB": {"last_price": 80},
            }

    config = KiteDataConfig(max_symbols=2, pause_seconds=0)

    results = find_kite_stocks_ltp_above_200_ema(config, kite=LtpTooCloseToHighKite())

    assert results == []


def test_find_kite_stocks_allows_zero_to_three_percent_entry_zone() -> None:
    class CloseToEmaKite(FakeKite):
        def ltp(self, instruments: list[str]) -> dict:
            return {
                "NSE:AAA": {"last_price": 325},
                "NSE:BBB": {"last_price": 80},
            }

    config = KiteDataConfig(max_symbols=2, pause_seconds=0)

    results = find_kite_stocks_ltp_above_200_ema(config, kite=CloseToEmaKite())

    assert [item.symbol for item in results] == ["AAA"]


def test_find_kite_stocks_allows_price_above_either_ema_10_or_ema_20() -> None:
    class BelowEma10Kite(FakeKite):
        def ltp(self, instruments: list[str]) -> dict:
            return {
                "NSE:AAA": {"last_price": 322},
                "NSE:BBB": {"last_price": 80},
            }

    config = KiteDataConfig(max_symbols=2, pause_seconds=0)

    results = find_kite_stocks_ltp_above_200_ema(config, kite=BelowEma10Kite())

    assert [item.symbol for item in results] == ["AAA"]


def test_rejects_when_short_emas_are_below_ema_200(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    rows = ["symbol,date,open,high,low,close,volume"]
    for index in range(210):
        close = 300 if index < 180 else 120 + index
        rows.append(f"AAA,2026-01-{(index % 28) + 1:02d},100,{close},90,{close},1500000")
    csv_path.write_text("\n".join(rows), encoding="utf-8")

    results = find_stocks_above_200_ema(csv_path)

    assert results == []
