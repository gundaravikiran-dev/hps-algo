from hps_algo import desktop_app


def test_port_check_reports_false_when_no_listener(monkeypatch) -> None:
    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def connect_ex(self, _address) -> int:
            return 1

    monkeypatch.setattr(desktop_app.socket, "socket", lambda *_args: FakeSocket())

    assert desktop_app._port_is_in_use() is False
