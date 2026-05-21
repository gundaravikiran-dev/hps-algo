from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_CANDLE_COLUMNS = ("date", "open", "high", "low", "close", "volume")


def load_candles_csv(path: str | Path) -> pd.DataFrame:
    candles = pd.read_csv(Path(path), parse_dates=["date"])
    missing = set(REQUIRED_CANDLE_COLUMNS).difference(candles.columns)
    if missing:
        raise ValueError(f"Missing candle columns: {sorted(missing)}")
    return candles.loc[:, REQUIRED_CANDLE_COLUMNS].sort_values("date").reset_index(drop=True)
