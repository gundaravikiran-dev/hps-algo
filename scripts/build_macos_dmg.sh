#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

APP_PATH="dist/HPS-Algo.app"
DMG_PATH="dist/HPS-Algo.dmg"
STAGING_DIR="build/dmg-root"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing $APP_PATH. Run 'make package-macos' first." >&2
  exit 1
fi

rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"
cp -R "$APP_PATH" "$STAGING_DIR/HPS-Algo.app"
ln -s /Applications "$STAGING_DIR/Applications"
rm -f "$DMG_PATH"

hdiutil create \
  -volname "HPS-Algo" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"
