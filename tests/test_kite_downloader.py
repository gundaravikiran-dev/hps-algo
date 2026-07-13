from pathlib import Path
from datetime import date

from hps_algo.data import (
    KiteDataConfig,
    download_nse_daily_candles,
    fetch_kite_historical_data,
    fetch_kite_historical_data_cached,
    filter_nse_equity_instruments,
    save_kite_instruments_to_store,
    save_technical_indicator_to_store,
)
from hps_algo.data.store import MarketDataStore


class FakeKite:
    def instruments(self, exchange: str) -> list[dict]:
        return [
            {
                "exchange": exchange,
                "segment": exchange,
                "instrument_type": "EQ",
                "tradingsymbol": "AAA",
                "name": "AAA INDUSTRIES",
                "instrument_token": 1,
            },
            {
                "exchange": exchange,
                "segment": exchange,
                "instrument_type": "EQ",
                "tradingsymbol": "BBB-BE",
                "name": "BBB LIMITED",
                "instrument_token": 2,
            },
            {
                "exchange": exchange,
                "segment": exchange,
                "instrument_type": "FUT",
                "tradingsymbol": "CCC",
                "name": "CCC LIMITED",
                "instrument_token": 3,
            },
        ]

    def historical_data(self, instrument_token, from_date, to_date, interval) -> list[dict]:
        return [
            {
                "date": from_date,
                "open": 100,
                "high": 110,
                "low": 95,
                "close": 105,
                "volume": 1_500_000,
            }
        ]


def test_filter_nse_equity_instruments() -> None:
    config = KiteDataConfig()

    selected = filter_nse_equity_instruments(FakeKite().instruments("NSE"), config)

    assert [item["tradingsymbol"] for item in selected] == ["AAA"]


def test_download_nse_daily_candles_writes_csv(tmp_path: Path) -> None:
    output_path = tmp_path / "candles.csv"
    config = KiteDataConfig(output_path=str(output_path), history_days=100, pause_seconds=0)

    summary = download_nse_daily_candles(config, kite=FakeKite())

    assert summary.symbols_downloaded == 1
    assert summary.rows_written == 1
    assert summary.selected_symbols == ["AAA"]
    assert "AAA" in output_path.read_text(encoding="utf-8")


def test_fetch_kite_historical_data_splits_long_ranges() -> None:
    class ChunkKite:
        def __init__(self) -> None:
            self.calls = []

        def historical_data(self, instrument_token, from_date, to_date, interval) -> list[dict]:
            self.calls.append((instrument_token, from_date, to_date, interval))
            return [{"date": from_date, "close": len(self.calls)}]

    kite = ChunkKite()
    candles = fetch_kite_historical_data(
        kite,
        101,
        date(2016, 1, 1),
        date(2025, 12, 29),
        "day",
    )

    assert len(candles) == 2
    assert kite.calls == [
        (101, date(2016, 1, 1), date(2021, 6, 22), "day"),
        (101, date(2021, 6, 23), date(2025, 12, 29), "day"),
    ]


def test_fetch_kite_historical_data_cached_reuses_local_store(tmp_path: Path) -> None:
    class CountingKite:
        def __init__(self) -> None:
            self.calls = 0

        def historical_data(self, instrument_token, from_date, to_date, interval) -> list[dict]:
            self.calls += 1
            return [
                {
                    "date": from_date,
                    "open": 100,
                    "high": 110,
                    "low": 95,
                    "close": 105,
                    "volume": 1_500_000,
                }
            ]

    kite = CountingKite()
    store_path = tmp_path / "market.sqlite3"

    first = fetch_kite_historical_data_cached(
        kite,
        101,
        date(2026, 1, 1),
        date(2026, 1, 10),
        "day",
        store_path=store_path,
    )
    second = fetch_kite_historical_data_cached(
        kite,
        101,
        date(2026, 1, 1),
        date(2026, 1, 10),
        "day",
        store_path=store_path,
    )

    assert kite.calls == 1
    assert first == second
    assert second[0]["close"] == 105


def test_fetch_kite_historical_data_cached_reads_timestamp_dates(tmp_path: Path) -> None:
    store_path = tmp_path / "market.sqlite3"
    store = MarketDataStore(store_path)
    with store._connect() as connection:
        connection.execute(
            """
            INSERT INTO candles (
                instrument_token,
                interval,
                candle_date,
                open,
                high,
                low,
                close,
                volume
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (101, "day", "2026-01-01T00:00:00+05:30", 100, 110, 95, 105, 1_500_000),
        )
    store.mark_synced_range(101, "day", date(2026, 1, 1), date(2026, 1, 10))

    candles = fetch_kite_historical_data_cached(
        FakeKite(),
        101,
        date(2026, 1, 1),
        date(2026, 1, 10),
        "day",
        store_path=store_path,
    )

    assert candles[0]["date"] == date(2026, 1, 1)
    assert candles[0]["close"] == 105


def test_fetch_kite_historical_data_cached_deduplicates_same_candle_date(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "market.sqlite3"
    store = MarketDataStore(store_path)
    with store._connect() as connection:
        connection.executemany(
            """
            INSERT INTO candles (
                instrument_token,
                interval,
                candle_date,
                open,
                high,
                low,
                close,
                volume
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (101, "day", "2026-01-01T00:00:00+05:30", 100, 110, 95, 105, 1000),
                (101, "day", "2026-01-01", 100, 110, 95, 105, 1000),
            ],
        )
    store.mark_synced_range(101, "day", date(2026, 1, 1), date(2026, 1, 10))

    candles = fetch_kite_historical_data_cached(
        FakeKite(),
        101,
        date(2026, 1, 1),
        date(2026, 1, 10),
        "day",
        store_path=store_path,
    )

    assert candles == [
        {
            "date": date(2026, 1, 1),
            "open": 100.0,
            "high": 110.0,
            "low": 95.0,
            "close": 105.0,
            "volume": 1000,
        }
    ]


def test_save_kite_instruments_to_store(tmp_path: Path) -> None:
    store_path = tmp_path / "market.sqlite3"

    save_kite_instruments_to_store(
        FakeKite().instruments("NSE"),
        store_path=store_path,
    )

    store = MarketDataStore(store_path)
    with store._connect() as connection:
        rows = connection.execute(
            """
            SELECT instrument_token, exchange, tradingsymbol, stock_name, instrument_type
            FROM instruments
            ORDER BY instrument_token
            """
        ).fetchall()

    assert [dict(row) for row in rows] == [
        {
            "instrument_token": 1,
            "exchange": "NSE",
            "tradingsymbol": "AAA",
            "stock_name": "AAA INDUSTRIES",
            "instrument_type": "EQ",
        },
        {
            "instrument_token": 2,
            "exchange": "NSE",
            "tradingsymbol": "BBB-BE",
            "stock_name": "BBB LIMITED",
            "instrument_type": "EQ",
        },
        {
            "instrument_token": 3,
            "exchange": "NSE",
            "tradingsymbol": "CCC",
            "stock_name": "CCC LIMITED",
            "instrument_type": "FUT",
        },
    ]


def test_save_technical_indicator_to_store(tmp_path: Path) -> None:
    store_path = tmp_path / "market.sqlite3"

    save_technical_indicator_to_store(
        101,
        "day",
        date(2026, 1, 10),
        100.1,
        99.2,
        95.3,
        80.4,
        64.5,
        120.0,
        140.0,
        store_path=store_path,
    )

    store = MarketDataStore(store_path)
    with store._connect() as connection:
        row = connection.execute(
            """
            SELECT instrument_token, interval, candle_date, ema_10, ema_20, ema_50,
                   ema_200, rsi_14, high_52w, all_time_high
            FROM technical_indicators
            """
        ).fetchone()

    assert dict(row) == {
        "instrument_token": 101,
        "interval": "day",
        "candle_date": "2026-01-10",
        "ema_10": 100.1,
        "ema_20": 99.2,
        "ema_50": 95.3,
        "ema_200": 80.4,
        "rsi_14": 64.5,
        "high_52w": 120.0,
        "all_time_high": 140.0,
    }
