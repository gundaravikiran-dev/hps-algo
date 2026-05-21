from __future__ import annotations

from hps_algo.data import KiteDataConfig
from hps_algo.strategies.hps_algo import (
    AboveEmaResult,
    KiteStrategyClient,
    find_kite_stocks_ltp_above_200_ema,
)


class AthAlgoStrategy:
    name = "ATH-Algo"

    def run(
        self,
        config: KiteDataConfig,
        kite: KiteStrategyClient | None = None,
    ) -> list[AboveEmaResult]:
        return find_kite_stocks_ltp_above_200_ema(
            config,
            kite=kite,
            require_high_distance=False,
        )
