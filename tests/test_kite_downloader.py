from pathlib import Path

from hps_algo.data import KiteDataConfig, download_nse_daily_candles, filter_nse_equity_instruments


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
    config = KiteDataConfig(output_path=str(output_path), pause_seconds=0)

    summary = download_nse_daily_candles(config, kite=FakeKite())

    assert summary.symbols_downloaded == 1
    assert summary.rows_written == 1
    assert summary.selected_symbols == ["AAA"]
    assert "AAA" in output_path.read_text(encoding="utf-8")
