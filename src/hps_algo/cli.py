from __future__ import annotations

import argparse

from hps_algo.data import KiteDataConfig, download_nse_daily_candles, load_kite_data_config
from hps_algo.kite_client import generate_access_token, login_url
from hps_algo.utils import configure_logging


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(prog="hps-algo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("login-url", help="Print the Kite login URL.")

    token_parser = subparsers.add_parser("access-token", help="Generate access token.")
    token_parser.add_argument("request_token")

    fetch_parser = subparsers.add_parser(
        "fetch-nse-data",
        help="Download NSE daily candles from Kite.",
    )
    fetch_parser.add_argument("--config", default="config/data.yaml")
    fetch_parser.add_argument("--max-symbols", type=int)
    fetch_parser.add_argument("--output")

    args = parser.parse_args()

    if args.command == "login-url":
        print(login_url())
        return

    if args.command == "access-token":
        print(generate_access_token(args.request_token))
        return

    if args.command == "fetch-nse-data":
        config = load_kite_data_config(args.config)
        if args.max_symbols is not None:
            config = KiteDataConfig(**{**config.__dict__, "max_symbols": args.max_symbols})
        if args.output:
            config = KiteDataConfig(**{**config.__dict__, "output_path": args.output})
        summary = download_nse_daily_candles(config)
        print(f"Output: {summary.output_path}")
        print(f"Instruments seen: {summary.instruments_seen}")
        print(f"Instruments selected: {summary.instruments_selected}")
        print(f"Symbols downloaded: {summary.symbols_downloaded}")
        print(f"Rows written: {summary.rows_written}")
        if summary.errors:
            print("Errors:")
            for error in summary.errors:
                print(f"- {error}")


if __name__ == "__main__":
    main()
