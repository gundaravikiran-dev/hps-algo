.PHONY: setup test lint ui package-macos package-dmg package-zip

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -e ".[dev]"

test:
	python3 -m pytest

lint:
	python3 -m ruff check src tests

ui:
	python3 -m hps_algo.ui.app

package-macos:
	./scripts/build_macos_app.sh

package-dmg:
	./scripts/build_macos_dmg.sh

package-zip:
	./scripts/build_macos_zip.sh
