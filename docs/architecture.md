# Project Architecture

The project is split by responsibility so the strategy rules can change without
forcing changes to broker, risk, data, or CLI code.

```text
hps_algo/
  broker/       Broker adapters: live Kite and paper trading
  data/         Candle loading and future market data sources
  domain/       Shared dataclasses and enums
  execution/    Run loop, order creation, and risk validation
  strategies/   Strategy interface and implementations
  utils/        Logging and operational helpers
```

## Runtime Flow

```text
config/strategy.yaml
        |
        v
CLI -> load candles -> strategy.evaluate()
        |                 |
        |                 v
        |            StrategyDecision
        |                 |
        v                 v
RiskManager <------ ExecutionEngine ------> Broker
                                      paper or Kite live
```

## Safety Defaults

- `dry_run: true` routes orders to `PaperBroker`.
- Live Kite order placement is isolated in `broker/kite.py`.
- Risk checks run before every order.
- Credentials are read from `.env`, which is ignored by git.

## Where Your Strategy Will Go

Your actual rules should be implemented as a new file under
`src/hps_algo/strategies/`, then registered in `src/hps_algo/factory.py`.
