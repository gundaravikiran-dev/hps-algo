from fastapi.testclient import TestClient

from hps_algo.ui.app import app


def test_ui_config_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json()["strategy"]["symbol"] == "RELIANCE"


def test_ui_index_uses_versioned_static_assets() -> None:
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "app.js?v=stock-txt-export-20260622-1" in response.text
    assert 'data-action="run-ema"' in response.text
    assert 'data-action="run-ema-pre-cross"' in response.text
    assert 'data-action="run-ema-pre-cross-10"' in response.text
    assert 'data-action="run-backtest"' in response.text
    assert 'data-action="export-txt"' in response.text
    assert 'id="backtestStrategyInput"' in response.text
    assert 'id="backtestDateInput"' in response.text
    assert response.headers["cache-control"] == "no-store"


def test_ui_kite_data_config_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/kite-data-config")

    assert response.status_code == 200
    assert response.json()["exchange"] == "NSE"


def test_ui_app_status_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/app/status")

    assert response.status_code == 200
    assert response.json() == {"app": "HPS-Algo", "status": "ready"}


def test_ui_shutdown_endpoint(monkeypatch) -> None:
    from hps_algo.ui import app as ui_app

    called = {"started": False}

    class ImmediateTimer:
        def __init__(self, _delay, _callback) -> None:
            self.callback = _callback

        def start(self) -> None:
            called["started"] = True

    monkeypatch.setattr(ui_app.threading, "Timer", ImmediateTimer)

    client = TestClient(app)
    response = client.post("/api/app/shutdown")

    assert response.status_code == 200
    assert response.json() == {"shutting_down": True}
    assert called["started"] is True


def test_ui_kite_callback_without_token() -> None:
    client = TestClient(app)
    response = client.get("/kite/callback")

    assert response.status_code == 200
    assert "Missing request token" in response.text


def test_ui_hps_algo_strategy_missing_data_message() -> None:
    client = TestClient(app)
    response = client.post("/api/strategy/hps-algo/run")

    assert response.status_code in {200, 400}


def test_ui_hps_algo_export_csv() -> None:
    client = TestClient(app)
    response = client.get("/api/strategy/hps-algo/export.csv")

    assert response.status_code in {200, 400}


def test_ui_ath_algo_endpoint() -> None:
    client = TestClient(app)
    response = client.post("/api/strategy/ath-algo/run")

    assert response.status_code in {200, 400}


def test_ui_ema_algo_endpoint() -> None:
    client = TestClient(app)
    response = client.post("/api/strategy/ema/run")

    assert response.status_code in {200, 400}


def test_ui_ema_pre_cross_algo_endpoint() -> None:
    client = TestClient(app)
    response = client.post("/api/strategy/ema-pre-cross/run")

    assert response.status_code in {200, 400}


def test_ui_ema_pre_cross_10_algo_endpoint() -> None:
    client = TestClient(app)
    response = client.post("/api/strategy/ema-pre-cross-10/run")

    assert response.status_code in {200, 400}


def test_fetch_request_defaults() -> None:
    from hps_algo.ui.app import FetchNseDataRequest

    request = FetchNseDataRequest()

    assert request.max_symbols is None
