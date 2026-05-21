from __future__ import annotations

from typing import Protocol

import pandas as pd

from hps_algo.domain import StrategyDecision


class Strategy(Protocol):
    name: str

    def evaluate(self, candles: pd.DataFrame) -> StrategyDecision:
        """Return the latest strategy decision for the given candles."""
