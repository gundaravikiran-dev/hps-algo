from datetime import date

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
    assert "app.js?v=momentum-export-menu-20260707-5" in response.text
    assert "Momentum Algo" in response.text
    assert "Login with Zerodha Kite" in response.text
    assert 'data-action="run-ema"' in response.text
    assert 'data-action="run-ema-pre-cross"' not in response.text
    assert 'data-action="run-ema-pre-cross-10"' not in response.text
    assert 'class="strategy-dropdown"' in response.text
    assert "Dashboard" in response.text
    assert "Reports" in response.text
    assert "Reset" in response.text
    assert "Export" in response.text
    assert 'id="exportMenu" class="export-menu is-disabled"' in response.text
    assert 'id="exportMenuButton"' in response.text
    assert "disabled" in response.text
    assert 'class="export-dropdown"' in response.text
    assert 'id="txtExportLink"' in response.text
    assert 'id="excelExportLink"' in response.text
    assert 'id="resultTitle"' in response.text
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
    assert response.json() == {"app": "Momentum Algo", "status": "ready"}


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


def test_ui_kite_callback_success_redirects_to_home(monkeypatch, tmp_path) -> None:
    from hps_algo.ui import app as ui_app

    env_path = tmp_path / ".env"
    monkeypatch.setattr(ui_app, "credentials_env_path", lambda: env_path)
    monkeypatch.setattr(ui_app, "generate_access_token", lambda _request_token: "access-token")

    client = TestClient(app, follow_redirects=False)
    response = client.get("/kite/callback?request_token=test-token")

    assert response.status_code == 303
    assert response.headers["location"] == "/?app=1"
    assert "KITE_ACCESS_TOKEN=access-token" in env_path.read_text(encoding="utf-8")


def test_ui_kite_credentials_endpoint_populates_saved_values(tmp_path, monkeypatch) -> None:
    from hps_algo.ui import app as ui_app

    env_path = tmp_path / ".env"
    env_path.write_text(
        "KITE_API_KEY=saved_key\nKITE_API_SECRET=saved_secret\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ui_app, "credentials_env_path", lambda: env_path)

    client = TestClient(app)
    response = client.get("/api/kite/credentials")

    assert response.status_code == 200
    assert response.json() == {
        "api_key": "saved_key",
        "api_secret": "saved_secret",
    }


def test_ui_hps_algo_strategy_missing_data_message() -> None:
    client = TestClient(app)
    response = client.post("/api/strategy/hps-algo/run")

    assert response.status_code in {200, 400}


def test_ui_hps_algo_export_txt() -> None:
    client = TestClient(app)
    response = client.get("/api/strategy/hps-algo/export.txt")

    assert response.status_code in {200, 400}
    if response.status_code == 200:
        assert (
            response.headers["content-disposition"]
            == f"attachment; filename=hps-algo_{date.today().isoformat()}.txt"
        )


def test_ui_ath_algo_export_txt() -> None:
    client = TestClient(app)
    response = client.get("/api/strategy/ath-algo/export.txt")

    assert response.status_code in {200, 400}


def test_ui_ema_export_txt() -> None:
    client = TestClient(app)
    response = client.get("/api/strategy/ema/export.txt")

    assert response.status_code in {200, 400}


def test_ui_ath_algo_export_excel() -> None:
    client = TestClient(app)
    response = client.get("/api/strategy/ath-algo/export.xls")

    assert response.status_code in {200, 400}
    if response.status_code == 200:
        assert (
            response.headers["content-disposition"]
            == f"attachment; filename=ath-algo_{date.today().isoformat()}.xls"
        )


def test_ui_ema_export_excel() -> None:
    client = TestClient(app)
    response = client.get("/api/strategy/ema/export.xls")

    assert response.status_code in {200, 400}


def test_ui_ath_algo_endpoint() -> None:
    client = TestClient(app)
    response = client.post("/api/strategy/ath-algo/run")

    assert response.status_code in {200, 400}


def test_ui_ema_algo_endpoint() -> None:
    client = TestClient(app)
    response = client.post("/api/strategy/ema/run")

    assert response.status_code in {200, 400}


def test_fetch_request_defaults() -> None:
    from hps_algo.ui.app import FetchNseDataRequest

    request = FetchNseDataRequest()

    assert request.max_symbols is None
