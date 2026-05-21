from __future__ import annotations

from typing import Protocol

from hps_algo.domain import OrderRequest, OrderResult


class Broker(Protocol):
    def place_order(self, order: OrderRequest) -> OrderResult:
        """Place or simulate an order."""
