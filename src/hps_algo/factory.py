from __future__ import annotations

from hps_algo.broker import KiteBroker, PaperBroker
from hps_algo.kite_client import build_kite
from hps_algo.settings import AppConfig
from hps_algo.strategies import Strategy


def build_strategy(config: AppConfig) -> Strategy:
    raise ValueError(f"No strategy is registered yet: {config.strategy.name}")


def build_broker(config: AppConfig) -> PaperBroker | KiteBroker:
    if config.strategy.dry_run:
        return PaperBroker()
    return KiteBroker(build_kite())
