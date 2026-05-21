from __future__ import annotations

import pandas as pd

from hps_algo.broker import Broker
from hps_algo.domain import OrderRequest, OrderResult, Signal, StrategyDecision
from hps_algo.execution.risk import RiskManager
from hps_algo.settings import AppConfig
from hps_algo.strategies import Strategy


class ExecutionEngine:
    def __init__(
        self,
        config: AppConfig,
        strategy: Strategy,
        broker: Broker,
        risk_manager: RiskManager,
    ) -> None:
        self._config = config
        self._strategy = strategy
        self._broker = broker
        self._risk_manager = risk_manager

    def run_once(self, candles: pd.DataFrame) -> tuple[StrategyDecision, OrderResult | None]:
        decision = self._strategy.evaluate(candles)
        if decision.signal == Signal.HOLD:
            return decision, None

        order = OrderRequest(
            symbol=self._config.strategy.symbol,
            exchange=self._config.strategy.exchange,
            transaction_type=decision.signal,
            quantity=self._config.strategy.quantity,
            product=self._config.strategy.product,
            order_type=self._config.strategy.order_type,
        )
        self._risk_manager.validate(order)
        result = self._broker.place_order(order)
        self._risk_manager.record_trade()
        return decision, result
