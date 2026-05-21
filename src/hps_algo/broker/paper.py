from __future__ import annotations

from hps_algo.domain import OrderRequest, OrderResult


class PaperBroker:
    def place_order(self, order: OrderRequest) -> OrderResult:
        return OrderResult(
            order_id=None,
            status="DRY_RUN",
            message=(
                f"{order.transaction_type.value} {order.quantity} "
                f"{order.exchange}:{order.symbol} as {order.order_type}"
            ),
        )
