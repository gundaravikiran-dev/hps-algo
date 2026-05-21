from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class StrategySettings(BaseModel):
    name: str
    symbol: str
    exchange: str = "NSE"
    interval: str = "5minute"
    product: str = "MIS"
    quantity: int = Field(gt=0)
    dry_run: bool = True
    order_type: str = "MARKET"


class RiskSettings(BaseModel):
    max_trades_per_day: int = Field(default=1, gt=0)
    stop_loss_pct: float = Field(default=0.5, gt=0)
    target_pct: float = Field(default=1.0, gt=0)
    max_order_quantity: int = Field(default=1, gt=0)
    allowed_trading_start: str = "09:20"
    allowed_trading_end: str = "15:10"


class AppConfig(BaseModel):
    strategy: StrategySettings
    risk: RiskSettings
    parameters: dict[str, Any] = Field(default_factory=dict)


def load_config(path: str | Path) -> AppConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return AppConfig.model_validate(raw)
