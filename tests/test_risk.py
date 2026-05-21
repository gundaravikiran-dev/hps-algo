import pytest

from hps_algo.domain import OrderRequest, Signal
from hps_algo.execution import RiskManager
from hps_algo.settings import RiskSettings


def test_rejects_quantity_above_limit() -> None:
    risk = RiskManager(RiskSettings(max_order_quantity=1))
    order = OrderRequest(
        symbol="RELIANCE",
        exchange="NSE",
        transaction_type=Signal.BUY,
        quantity=2,
        product="MIS",
        order_type="MARKET",
    )

    with pytest.raises(ValueError, match="quantity"):
        risk.validate(order)
