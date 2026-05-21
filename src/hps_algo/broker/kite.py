from __future__ import annotations

from kiteconnect import KiteConnect

from hps_algo.domain import OrderRequest, OrderResult, Signal


class KiteBroker:
    def __init__(self, kite: KiteConnect) -> None:
        self._kite = kite

    def place_order(self, order: OrderRequest) -> OrderResult:
        transaction_type = (
            self._kite.TRANSACTION_TYPE_BUY
            if order.transaction_type == Signal.BUY
            else self._kite.TRANSACTION_TYPE_SELL
        )

        order_id = self._kite.place_order(
            variety=self._kite.VARIETY_REGULAR,
            exchange=order.exchange,
            tradingsymbol=order.symbol,
            transaction_type=transaction_type,
            quantity=order.quantity,
            product=order.product,
            order_type=order.order_type,
            validity=self._kite.VALIDITY_DAY,
            tag=order.tag,
        )
        return OrderResult(order_id=order_id, status="PLACED", message="Order placed.")
