from hps_algo.data import KiteDataConfig
from hps_algo.strategies.ema_algo import (
    EmaStrategy,
    _ema_10_above_20_within_distance,
    find_kite_stocks_price_above_200_ema,
)
from tests.test_hps_algo_strategy import FakeKite


class EmaFriendlyKite(FakeKite):
    def historical_data(self, instrument_token, from_date, to_date, interval) -> list[dict]:
        if instrument_token == 1:
            return [
                {"close": 300 + (index * 0.05), "high": 300 + (index * 0.05)}
                for index in range(230)
            ]
        return [{"close": 300 - index, "high": 300 - index} for index in range(230)]

    def ltp(self, instruments: list[str]) -> dict:
        return {
            "NSE:AAA": {"last_price": 312},
            "NSE:BBB": {"last_price": 80},
        }


def test_ema_algo_lists_stocks_with_ltp_above_ema_200() -> None:
    strategy = EmaStrategy()

    results = strategy.run(KiteDataConfig(max_symbols=2, pause_seconds=0), kite=EmaFriendlyKite())

    assert strategy.name == "EMA"
    assert [item.symbol for item in results] == ["AAA"]
    assert results[0].ltp > results[0].ema_200
    assert results[0].ema_10 > results[0].ema_200
    assert results[0].ema_20 > results[0].ema_200
    assert results[0].ema_50 > results[0].ema_200
    assert results[0].ema_10 >= results[0].ema_20
    assert results[0].ema_10 - results[0].ema_20 <= 1
    assert results[0].condition == (
        "Price, EMA10, EMA20, EMA50 > EMA200; EMA10 >= EMA20 within 1"
    )
    assert results[0].entry_zone == "Within 1.5% of EMA10, EMA20, EMA50"
    assert 0 <= results[0].above_ema_10_pct <= 1.5
    assert 0 <= results[0].above_ema_20_pct <= 1.5
    assert 0 <= results[0].above_ema_50_pct <= 1.5


def test_ema_algo_returns_empty_when_price_is_below_ema_200() -> None:
    class BelowEmaKite(FakeKite):
        def ltp(self, instruments: list[str]) -> dict:
            return {
                "NSE:AAA": {"last_price": 80},
                "NSE:BBB": {"last_price": 80},
            }

    results = find_kite_stocks_price_above_200_ema(
        KiteDataConfig(max_symbols=2, pause_seconds=0),
        kite=BelowEmaKite(),
    )

    assert results == []


def test_ema_10_20_distance_allows_equal_values() -> None:
    assert _ema_10_above_20_within_distance(150, 150) is True
    assert _ema_10_above_20_within_distance(150.1, 150) is True
    assert _ema_10_above_20_within_distance(151.1, 150) is False
    assert _ema_10_above_20_within_distance(149.9, 150) is False


def test_ema_algo_returns_empty_when_ema_10_is_too_far_above_ema_20() -> None:
    class Ema10TooFarAbove20Kite(EmaFriendlyKite):
        def historical_data(self, instrument_token, from_date, to_date, interval) -> list[dict]:
            if instrument_token == 1:
                return [
                    {"close": 100 + index, "high": 100 + index}
                    for index in range(230)
                ]
            return super().historical_data(instrument_token, from_date, to_date, interval)

        def ltp(self, instruments: list[str]) -> dict:
            return {
                "NSE:AAA": {"last_price": 326},
                "NSE:BBB": {"last_price": 80},
            }

    results = find_kite_stocks_price_above_200_ema(
        KiteDataConfig(max_symbols=2, pause_seconds=0),
        kite=Ema10TooFarAbove20Kite(),
    )

    assert results == []


def test_ema_algo_returns_empty_when_price_is_far_above_any_short_ema() -> None:
    class FarAboveAnyShortEmaKite(EmaFriendlyKite):
        def ltp(self, instruments: list[str]) -> dict:
            return {
                "NSE:AAA": {"last_price": 316},
                "NSE:BBB": {"last_price": 316},
            }

    results = find_kite_stocks_price_above_200_ema(
        KiteDataConfig(max_symbols=2, pause_seconds=0),
        kite=FarAboveAnyShortEmaKite(),
    )

    assert results == []


def test_ema_algo_returns_empty_when_short_emas_are_below_ema_200() -> None:
    class ShortEmasBelowKite(FakeKite):
        def historical_data(self, instrument_token, from_date, to_date, interval) -> list[dict]:
            return [{"close": 300 - index, "high": 300 - index} for index in range(230)]

        def ltp(self, instruments: list[str]) -> dict:
            return {
                "NSE:AAA": {"last_price": 500},
                "NSE:BBB": {"last_price": 500},
            }

    results = find_kite_stocks_price_above_200_ema(
        KiteDataConfig(max_symbols=2, pause_seconds=0),
        kite=ShortEmasBelowKite(),
    )

    assert results == []
