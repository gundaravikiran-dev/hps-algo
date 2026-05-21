from fastapi.testclient import TestClient

from hps_algo.ui.app import app


def test_ui_config_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json()["strategy"]["symbol"] == "RELIANCE"


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


def test_fetch_request_defaults() -> None:
    from hps_algo.ui.app import FetchNseDataRequest

    request = FetchNseDataRequest()

    assert request.max_symbols is None
