from pathlib import Path

from hps_algo.settings import load_config


def test_load_config() -> None:
    config = load_config(Path("config/strategy.yaml"))

    assert config.strategy.symbol == "RELIANCE"
    assert config.strategy.dry_run is True
    assert config.risk.max_order_quantity == 10
