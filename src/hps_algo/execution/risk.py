from __future__ import annotations

from hps_algo.domain import OrderRequest
from hps_algo.settings import RiskSettings


class RiskManager:
    def __init__(self, settings: RiskSettings) -> None:
        self._settings = settings
        self._trades_today = 0

    def validate(self, order: OrderRequest) -> None:
        if self._trades_today >= self._settings.max_trades_per_day:
            raise ValueError("Max trades per day reached.")
        if order.quantity > self._settings.max_order_quantity:
            raise ValueError("Order quantity exceeds configured max_order_quantity.")

    def record_trade(self) -> None:
        self._trades_today += 1
