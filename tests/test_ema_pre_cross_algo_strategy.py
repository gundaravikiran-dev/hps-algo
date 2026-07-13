from hps_algo.data import KiteDataConfig
from hps_algo.strategies.ema_pre_cross_algo import (
    EmaPreCross10Strategy,
    EmaPreCrossStrategy,
    _ema_10_cross_condition,
    _ema_10_cross_distance_valid,
    _ema_10_crossed_above,
    _previous_10_plus_ema_alignment,
    find_kite_stocks_for_ema_pre_cross,
    find_kite_stocks_for_ema_pre_cross_10,
)
from tests.test_hps_algo_strategy import FakeKite


class EmaPreCrossFriendlyKite(FakeKite):
    def historical_data(self, instrument_token, from_date, to_date, interval) -> list[dict]:
        if instrument_token == 1:
            return [
                {"close": 300, "high": 300}
                for _ in range(220)
            ] + [
                {"close": 299, "high": 299}
                for _ in range(5)
            ] + [
                {"close": 305, "high": 305},
            ]
        return [{"close": 300 - index, "high": 300 - index} for index in range(230)]

    def ltp(self, instruments: list[str]) -> dict:
        return {
            "NSE:AAA": {"last_price": 305},
            "NSE:BBB": {"last_price": 80},
        }


class EmaPreCross10FriendlyKite(FakeKite):
    def historical_data(self, instrument_token, from_date, to_date, interval) -> list[dict]:
        if instrument_token == 1:
            return [
                {"close": 300, "high": 300}
                for _ in range(220)
            ] + [
                {"close": 299, "high": 299}
                for _ in range(10)
            ] + [
                {"close": 308, "high": 308},
            ]
        return [{"close": 300 - index, "high": 300 - index} for index in range(240)]

    def ltp(self, instruments: list[str]) -> dict:
        return {
            "NSE:AAA": {"last_price": 308},
            "NSE:BBB": {"last_price": 80},
        }


def test_ema_pre_cross_lists_stocks_with_ltp_above_ema_200() -> None:
    strategy = EmaPreCrossStrategy()

    results = strategy.run(
        KiteDataConfig(max_symbols=2, pause_seconds=0),
        kite=EmaPreCrossFriendlyKite(),
    )

    assert strategy.name == "EMA_PRE_CROSS"
    assert [item.symbol for item in results] == ["AAA"]
    assert results[0].ltp > results[0].ema_200
    assert results[0].ema_10 > 0
    assert results[0].ema_20 > 0
    assert results[0].ema_50 > 0
    assert results[0].ema_10 > results[0].ema_20
    assert results[0].ema_10 > results[0].ema_50
    assert results[0].ema_10 > results[0].ema_200
    assert results[0].ema_20 > results[0].ema_200
    assert results[0].ema_50 > results[0].ema_200
    assert results[0].ema_10 - results[0].ema_20 <= 1
    assert results[0].ema_10 - results[0].ema_50 <= 1
    assert results[0].condition == "EMA10 crossed above EMA20 and EMA50; crossed EMA distance <= 1"
    assert results[0].entry_zone == "Not Applied"


def test_ema_pre_cross_10_requires_previous_10_ema_stack_before_cross() -> None:
    strategy = EmaPreCross10Strategy()

    results = strategy.run(
        KiteDataConfig(max_symbols=2, pause_seconds=0),
        kite=EmaPreCross10FriendlyKite(),
    )

    assert strategy.name == "EMA_PRE_CROSS_10"
    assert [item.symbol for item in results] == ["AAA"]
    assert results[0].ema_10 > results[0].ema_20
    assert results[0].ema_10 > results[0].ema_50
    assert results[0].condition == (
        "EMA10 crossed above EMA20; previous 10+ EMA10 < EMA20 < EMA50; "
        "crossed EMA distance <= 1"
    )


def test_ema_pre_cross_10_returns_empty_when_previous_stack_is_missing() -> None:
    results = find_kite_stocks_for_ema_pre_cross_10(
        KiteDataConfig(max_symbols=2, pause_seconds=0),
        kite=EmaPreCrossFriendlyKite(),
    )

    assert results == []


def test_ema_pre_cross_returns_empty_when_ltp_is_below_ema_200() -> None:
    class BelowEmaKite(EmaPreCrossFriendlyKite):
        def ltp(self, instruments: list[str]) -> dict:
            return {
                "NSE:AAA": {"last_price": 80},
                "NSE:BBB": {"last_price": 80},
            }

    results = find_kite_stocks_for_ema_pre_cross(
        KiteDataConfig(max_symbols=2, pause_seconds=0),
        kite=BelowEmaKite(),
    )

    assert results == []


def test_ema_pre_cross_condition_detects_cross_above_reference() -> None:
    assert _ema_10_crossed_above(149.5, 150, 150.5, 150) is True
    assert _ema_10_crossed_above(150, 150, 150.5, 150) is True
    assert _ema_10_crossed_above(150.5, 150, 151, 150.5) is False


def test_ema_pre_cross_condition_can_limit_cross_to_ema_20() -> None:
    import pandas as pd

    data = pd.DataFrame(
        {
            "ema_10": [99.0, 102.0],
            "ema_20": [100.0, 101.0],
            "ema_50": [101.0, 101.5],
        }
    )

    condition = _ema_10_cross_condition(data, reference_names=("EMA20",))

    assert condition is not None
    assert condition.label == "EMA10 crossed above EMA20"
    assert condition.crossed_references == ("EMA20",)


def test_ema_pre_cross_distance_requires_max_one_point_when_ema_10_is_above() -> None:
    assert _ema_10_cross_distance_valid(151, 150, 149, ("EMA20",)) is True
    assert _ema_10_cross_distance_valid(151.1, 150, 151, ("EMA20",)) is False
    assert _ema_10_cross_distance_valid(151.1, 149, 150.2, ("EMA20", "EMA50")) is True
    assert _ema_10_cross_distance_valid(151.1, 149, 150.2, ("EMA20",)) is False


def test_previous_10_plus_ema_alignment_checks_consecutive_completed_candles() -> None:
    import pandas as pd

    aligned = pd.DataFrame(
        {
            "ema_10": [101, *([99] * 12), 102],
            "ema_20": [101, *([100] * 12), 101],
            "ema_50": [101, *([101] * 12), 100],
        }
    )
    not_aligned = pd.DataFrame(
        {
            "ema_10": [101, *([100] * 10), 102],
            "ema_20": [101, *([100] * 10), 101],
            "ema_50": [101, *([101] * 10), 100],
        }
    )

    assert _previous_10_plus_ema_alignment(aligned) is True
    assert _previous_10_plus_ema_alignment(not_aligned) is False


def test_ema_pre_cross_returns_empty_when_ema_10_distance_is_too_wide() -> None:
    class WideCrossKite(EmaPreCrossFriendlyKite):
        def historical_data(self, instrument_token, from_date, to_date, interval) -> list[dict]:
            if instrument_token == 1:
                return [
                    {"close": 100 - (index * 0.02), "high": 100 - (index * 0.02)}
                    for index in range(200)
                ] + [
                    {"close": 156, "high": 156},
                ]
            return super().historical_data(instrument_token, from_date, to_date, interval)

        def ltp(self, instruments: list[str]) -> dict:
            return {
                "NSE:AAA": {"last_price": 156},
                "NSE:BBB": {"last_price": 80},
            }

    results = find_kite_stocks_for_ema_pre_cross(
        KiteDataConfig(max_symbols=2, pause_seconds=0),
        kite=WideCrossKite(),
    )

    assert results == []


def test_ema_pre_cross_returns_empty_when_short_emas_are_below_ema_200() -> None:
    class ShortEmasBelowKite(EmaPreCrossFriendlyKite):
        def historical_data(self, instrument_token, from_date, to_date, interval) -> list[dict]:
            return [{"close": 300 - index, "high": 300 - index} for index in range(230)]

        def ltp(self, instruments: list[str]) -> dict:
            return {
                "NSE:AAA": {"last_price": 500},
                "NSE:BBB": {"last_price": 500},
            }

    results = find_kite_stocks_for_ema_pre_cross(
        KiteDataConfig(max_symbols=2, pause_seconds=0),
        kite=ShortEmasBelowKite(),
    )

    assert results == []
