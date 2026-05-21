import pandas as pd

from hps_algo.broker import PaperBroker
from hps_algo.domain import Signal, StrategyDecision
from hps_algo.execution import ExecutionEngine, RiskManager
from hps_algo.settings import load_config


class HoldStrategy:
    name = "hold_for_test"

    def evaluate(self, candles: pd.DataFrame) -> StrategyDecision:
        return StrategyDecision(
            signal=Signal.HOLD,
            reason="Test strategy holds.",
            last_price=float(candles["close"].iloc[-1]),
        )


def test_engine_runs_with_paper_broker() -> None:
    config = load_config("config/strategy.yaml")
    candles = pd.DataFrame(
        [
            {
                "date": "2026-05-12",
                "open": 100,
                "high": 125,
                "low": 95,
                "close": 123,
                "volume": 1_000_000,
            }
        ]
    )
    engine = ExecutionEngine(
        config=config,
        strategy=HoldStrategy(),
        broker=PaperBroker(),
        risk_manager=RiskManager(config.risk),
    )

    decision, order = engine.run_once(candles)

    assert decision.last_price == 123
    assert order is None or order.status == "DRY_RUN"
