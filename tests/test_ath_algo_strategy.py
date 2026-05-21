from hps_algo.data import KiteDataConfig
from hps_algo.strategies.ath_algo import AthAlgoStrategy
from tests.test_hps_algo_strategy import FakeKite


def test_ath_algo_runs_without_high_distance_filter() -> None:
    strategy = AthAlgoStrategy()

    results = strategy.run(KiteDataConfig(max_symbols=2, pause_seconds=0), kite=FakeKite())

    assert strategy.name == "ATH-Algo"
    assert [item.symbol for item in results] == ["AAA"]
    assert results[0].high_reference == "Not Applied"
