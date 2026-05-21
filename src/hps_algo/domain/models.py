from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Candle:
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class StrategyDecision:
    signal: Signal
    reason: str
    last_price: float


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    exchange: str
    transaction_type: Signal
    quantity: int
    product: str
    order_type: str
    tag: str = "hps_algo"


@dataclass(frozen=True)
class OrderResult:
    order_id: str | None
    status: str
    message: str
