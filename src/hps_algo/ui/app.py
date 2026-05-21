from __future__ import annotations

import os
import signal
import threading
from pathlib import Path
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from hps_algo.data import (
    KiteDataConfig,
    download_nse_daily_candles,
    load_kite_data_config,
)
from hps_algo.kite_client import (
    credential_status,
    generate_access_token,
    has_access_token,
    login_url,
    save_access_token,
    save_credentials,
)
from hps_algo.runtime_paths import config_path, credentials_env_path, state_root, ui_assets_dir
from hps_algo.settings import load_config
from hps_algo.strategies.ath_algo import AthAlgoStrategy
from hps_algo.strategies.hps_algo import find_kite_stocks_ltp_above_200_ema

STATE_ROOT = state_root()
CONFIG_PATH = config_path("strategy.yaml")
DATA_CONFIG_PATH = config_path("data.yaml")
UI_DIR = ui_assets_dir()

app = FastAPI(title="HPS-Algo UI")
app.mount("/static", StaticFiles(directory=UI_DIR / "static"), name="static")


class FetchNseDataRequest(BaseModel):
    max_symbols: int | None = None
    output_path: str | None = None


class KiteCredentialsRequest(BaseModel):
    api_key: str
    api_secret: str


@app.get("/")
def index() -> FileResponse:
    return FileResponse(UI_DIR / "templates" / "index.html")


@app.get("/api/config")
def get_config() -> dict:
    config = load_config(CONFIG_PATH)
    return config.model_dump()


@app.get("/api/kite-data-config")
def get_kite_data_config() -> dict:
    return load_kite_data_config(DATA_CONFIG_PATH).__dict__


@app.get("/api/kite/status")
def kite_status() -> dict:
    return {"connected": has_access_token()}


@app.get("/api/app/status")
def app_status() -> dict:
    return {"app": "HPS-Algo", "status": "ready"}


@app.post("/api/app/shutdown")
def shutdown_app() -> dict:
    threading.Timer(0.35, _stop_process).start()
    return {"shutting_down": True}


@app.get("/api/kite/credentials/status")
def kite_credentials_status() -> dict:
    return credential_status()


@app.post("/api/kite/credentials")
def save_kite_credentials(request: KiteCredentialsRequest) -> dict:
    try:
        save_credentials(request.api_key, request.api_secret, credentials_env_path())
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {"saved": True}


@app.get("/api/kite/login-url")
def kite_login_url() -> dict:
    try:
        return {"login_url": login_url()}
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/kite/callback", response_class=HTMLResponse)
def kite_callback(request_token: str | None = None, status: str | None = None) -> str:
    if status and status.lower() != "success":
        return _callback_html("Kite login failed", f"Status: {status}")

    if not request_token:
        return _callback_html("Missing request token", "Kite did not send a request_token.")

    try:
        access_token = generate_access_token(request_token)
        save_access_token(access_token, credentials_env_path())
    except Exception as error:
        return _callback_html("Access token failed", str(error))

    return _callback_html("Kite connected", "Access token saved. Continue to the strategy workspace.")


@app.post("/api/kite/fetch-nse-data")
def fetch_nse_data(request: FetchNseDataRequest) -> dict:
    config = load_kite_data_config(DATA_CONFIG_PATH)
    updates = config.__dict__.copy()
    if request.max_symbols is not None:
        updates["max_symbols"] = request.max_symbols
    if request.output_path:
        output_path = _resolve_project_path(request.output_path)
        updates["output_path"] = str(output_path)

    try:
        summary = download_nse_daily_candles(KiteDataConfig(**updates))
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return summary.to_dict()


@app.post("/api/strategy/hps-algo/run")
def run_hps_algo_strategy() -> dict:
    data_config = load_kite_data_config(DATA_CONFIG_PATH)

    try:
        results = find_kite_stocks_ltp_above_200_ema(data_config)
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {
        "count": len(results),
        "source": "Kite API: historical daily candles + LTP",
        "results": [item.to_dict() for item in results],
    }


@app.post("/api/strategy/ath-algo/run")
def run_ath_algo_strategy() -> dict:
    data_config = load_kite_data_config(DATA_CONFIG_PATH)
    strategy = AthAlgoStrategy()
    try:
        results = strategy.run(data_config)
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {
        "count": len(results),
        "source": "Kite API: HPS-Algo rules without ATH/52W distance filter",
        "results": [item.to_dict() for item in results],
    }


@app.get("/api/strategy/hps-algo/export.csv")
def export_hps_algo_csv() -> Response:
    payload = run_hps_algo_strategy()
    csv_text = _strategy_results_to_csv(payload["results"])
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hps-algo-results.csv"},
    )


@app.get("/api/strategy/hps-algo/export.xls")
def export_hps_algo_excel() -> Response:
    payload = run_hps_algo_strategy()
    csv_text = _strategy_results_to_csv(payload["results"])
    filename = quote("hps-algo-results.xls")
    return Response(
        content=csv_text,
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _resolve_project_path(path: str) -> Path:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = STATE_ROOT / resolved
    return resolved


def _strategy_results_to_csv(results: list[dict]) -> str:
    columns = [
        "symbol",
        "ltp",
        "ema_10",
        "ema_20",
        "ema_200",
        "rsi_14",
        "condition",
        "entry_zone",
        "above_ema_10_pct",
        "above_ema_20_pct",
        "high_reference",
        "high_price",
        "below_high_pct",
    ]
    lines = [",".join(columns)]
    for item in results:
        lines.append(",".join(str(item.get(column, "")) for column in columns))
    return "\n".join(lines) + "\n"


def _callback_html(title: str, message: str) -> str:
    return f"""
    <!doctype html>
    <html>
      <head>
        <title>HPS-Algo Kite Login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
          body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            background: #f3f6f8;
            color: #172026;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          }}
          main {{
            width: min(520px, calc(100vw - 32px));
            background: #ffffff;
            border: 1px solid #d9e0e6;
            border-radius: 8px;
            padding: 24px;
          }}
          h1 {{ margin: 0 0 12px; font-size: 26px; }}
          p {{ margin: 0 0 18px; color: #63717d; }}
          a {{
            display: inline-flex;
            min-height: 42px;
            align-items: center;
            border-radius: 6px;
            background: #0f766e;
            color: white;
            padding: 0 16px;
            text-decoration: none;
            font-weight: 800;
          }}
        </style>
      </head>
      <body>
        <main>
          <h1>{title}</h1>
          <p>{message}</p>
          <a href="/?app=1">Back to HPS-Algo</a>
        </main>
      </body>
    </html>
    """


def _stop_process() -> None:
    os.kill(os.getpid(), signal.SIGTERM)


def main() -> None:
    uvicorn.run("hps_algo.ui.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
