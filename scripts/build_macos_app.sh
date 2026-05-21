#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
.venv/bin/python -m PyInstaller packaging/HPS-Algo.spec --noconfirm --clean
