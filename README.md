# HPS-Algo

Architecture-first Python framework for Zerodha Kite Connect strategies.

This repo is set up so we can add your real strategy after the foundations are
clear: configuration, broker abstraction, risk checks, data loading, execution,
tests, and documentation.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Fill `.env` with your Kite Connect API key and secret. Do not commit `.env`.

## Architecture

```text
src/hps_algo/
  broker/       Paper broker and live Kite broker adapter
  data/         Candle loading
  domain/       Shared trading models
  execution/    Engine and risk checks
  strategies/   Strategy interface and implementations
  utils/        Logging helpers
```

See [docs/architecture.md](docs/architecture.md) for the runtime flow.

## Login Flow

```bash
hps-algo login-url
hps-algo access-token REQUEST_TOKEN_FROM_REDIRECT
```

Put the generated access token into `.env` as `KITE_ACCESS_TOKEN`.

For the UI login flow, set your Kite app redirect URL to:

```text
http://127.0.0.1:8000/kite/callback
```

Then start `hps-algo-ui` and use the Login button. The callback saves the
generated access token into your local `.env`.

## Run The UI

```bash
make ui
```

Open:

```text
http://127.0.0.1:8000
```

The UI provides Kite login, data fetch controls, and a clean workspace for the
next strategy.

## Package A macOS App

Phase 1 packaging creates a local macOS `.app` bundle for non-developer users.
The app opens the browser UI automatically, and saves API credentials in:

```text
~/Library/Application Support/HPS-Algo/.env
```

Install the packaging dependency once:

```bash
pip install -e ".[package]"
```

Build the app:

```bash
make package-macos
```

The bundle is created at:

```text
dist/HPS-Algo.app
```

The packaged launcher keeps Kite on the fixed local callback port `8000`. If
HPS-Algo is already running, opening the app again reopens the existing browser
UI. If another local app is using port `8000`, HPS-Algo opens a clear startup
message instead of failing silently.

Create a shareable DMG after the app bundle is built:

```bash
make package-dmg
```

The installer image is created at:

```text
dist/HPS-Algo.dmg
```

Open the DMG and drag `HPS-Algo.app` into `Applications`.

Create a direct ZIP of the macOS app bundle:

```bash
make package-zip
```

The ZIP archive is created at:

```text
dist/HPS-Algo-macOS.zip
```

## Package For Windows

Windows builds must be created on a Windows machine. PyInstaller does not
cross-compile Windows executables from macOS.

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[package]"
.\scripts\build_windows_app.ps1
```

This creates:

```text
dist\HPS-Algo\
```

The folder contains the Windows launcher and its support files. Create a ZIP
for sharing:

```powershell
.\scripts\build_windows_zip.ps1
```

The Windows ZIP is written to:

```text
dist\HPS-Algo-Windows.zip
```

## Fetch NSE Data From Kite

After Kite login succeeds and `.env` has `KITE_ACCESS_TOKEN`, fetch daily NSE
candles:

```bash
hps-algo fetch-nse-data --max-symbols 50
```

This writes:

```text
data/nse_daily_candles.csv
```

The fetch settings live in [config/data.yaml](config/data.yaml). Start with a
small symbol limit, then increase it once the flow is working.

Order placement is disabled by default through `dry_run: true` in
`config/strategy.yaml`. Keep it enabled until the strategy has been tested.

## Quality Checks

```bash
make test
make lint
```

## Next Strategy Inputs Needed

Share these and I will implement the new strategy:

- Segment: equity, futures, options, or commodity
- Instruments: symbols or index/options universe
- Timeframe: 1m, 3m, 5m, 15m, daily, etc.
- Entry conditions
- Exit conditions
- Stop loss and target rules
- Quantity or capital allocation
- Max trades per day
- Trading time window
- Paper trading first, or live orders after confirmation

This project is software scaffolding, not financial advice. Test with paper
trading before using real money.
