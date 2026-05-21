#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

APP_PATH="dist/HPS-Algo.app"
ZIP_PATH="dist/HPS-Algo-macOS.zip"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing $APP_PATH. Run 'make package-macos' first." >&2
  exit 1
fi

rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
