from __future__ import annotations

import json
import socket
import threading
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

from hps_algo.runtime_paths import state_root
from hps_algo.ui.app import main as run_ui

APP_URL = "http://127.0.0.1:8000/"
APP_STATUS_URL = f"{APP_URL}api/app/status"
HOST = "127.0.0.1"
PORT = 8000


def main() -> None:
    _activate_regular_macos_app()

    if _port_is_in_use():
        if _hps_algo_is_running():
            webbrowser.open(APP_URL)
            return

        webbrowser.open(_write_port_error_page().as_uri())
        return

    browser_timer = threading.Timer(1.0, webbrowser.open, args=(APP_URL,))
    browser_timer.daemon = True
    browser_timer.start()
    run_ui()


def _activate_regular_macos_app() -> None:
    try:
        from AppKit import (
            NSApplication,
            NSApplicationActivationPolicyRegular,
        )
    except ImportError:
        return

    application = NSApplication.sharedApplication()
    application.setActivationPolicy_(NSApplicationActivationPolicyRegular)


def _port_is_in_use() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex((HOST, PORT)) == 0


def _hps_algo_is_running() -> bool:
    try:
        with urlopen(APP_STATUS_URL, timeout=1.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, URLError, OSError, json.JSONDecodeError):
        return False

    return payload.get("app") == "HPS-Algo"


def _write_port_error_page() -> Path:
    output_path = state_root() / "startup-error.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>HPS-Algo Startup</title>
    <style>
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: #f3f6f8;
        color: #172026;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      main {
        width: min(640px, calc(100vw - 32px));
        border: 1px solid #d9e0e6;
        border-radius: 8px;
        background: #ffffff;
        padding: 28px;
      }
      h1 { margin: 0 0 12px; font-size: 28px; }
      p { margin: 0 0 12px; color: #63717d; line-height: 1.5; }
      code { color: #172026; font-weight: 700; }
    </style>
  </head>
  <body>
    <main>
      <h1>HPS-Algo could not start</h1>
      <p>Local port <code>8000</code> is already being used by another app.</p>
      <p>Close the app using that port, then open HPS-Algo again.</p>
      <p>The fixed port is required because the Kite redirect URL is <code>http://127.0.0.1:8000/kite/callback</code>.</p>
    </main>
  </body>
</html>
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return output_path


if __name__ == "__main__":
    main()
