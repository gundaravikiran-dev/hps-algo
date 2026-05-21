from __future__ import annotations

import shutil
import sys
from pathlib import Path

APP_NAME = "HPS-Algo"


def is_packaged_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundled_root() -> Path:
    if is_packaged_app():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[2]


def state_root() -> Path:
    if is_packaged_app():
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return bundled_root()


def credentials_env_path() -> Path:
    return state_root() / ".env"


def ui_assets_dir() -> Path:
    if is_packaged_app():
        return bundled_root() / "hps_algo" / "ui"
    return Path(__file__).resolve().parent / "ui"


def config_path(filename: str) -> Path:
    target = state_root() / "config" / filename
    if not is_packaged_app():
        return target

    source = bundled_root() / "config" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(source, target)
    return target
