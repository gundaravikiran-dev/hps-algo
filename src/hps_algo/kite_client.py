from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from kiteconnect import KiteConnect

from hps_algo.runtime_paths import credentials_env_path


@dataclass(frozen=True)
class KiteCredentials:
    api_key: str
    api_secret: str
    access_token: str | None = None


def load_credentials() -> KiteCredentials:
    load_dotenv(dotenv_path=credentials_env_path(), override=True)
    api_key = os.getenv("KITE_API_KEY", "").strip()
    api_secret = os.getenv("KITE_API_SECRET", "").strip()
    access_token = os.getenv("KITE_ACCESS_TOKEN", "").strip() or None

    if not api_key or not api_secret:
        raise RuntimeError("Set KITE_API_KEY and KITE_API_SECRET in .env before using Kite.")

    return KiteCredentials(api_key=api_key, api_secret=api_secret, access_token=access_token)


def build_kite(access_token_required: bool = True) -> KiteConnect:
    credentials = load_credentials()
    kite = KiteConnect(api_key=credentials.api_key)

    if credentials.access_token:
        kite.set_access_token(credentials.access_token)
    elif access_token_required:
        raise RuntimeError("Set KITE_ACCESS_TOKEN in .env or generate one with the login flow.")

    return kite


def login_url() -> str:
    return build_kite(access_token_required=False).login_url()


def generate_access_token(request_token: str) -> str:
    credentials = load_credentials()
    kite = KiteConnect(api_key=credentials.api_key)
    session = kite.generate_session(request_token, api_secret=credentials.api_secret)
    return session["access_token"]


def save_access_token(access_token: str, env_path: str | Path = ".env") -> None:
    _write_env_values({"KITE_ACCESS_TOKEN": access_token}, env_path)
    os.environ["KITE_ACCESS_TOKEN"] = access_token


def save_credentials(api_key: str, api_secret: str, env_path: str | Path = ".env") -> None:
    cleaned_api_key = api_key.strip()
    cleaned_api_secret = api_secret.strip()
    if not cleaned_api_key or not cleaned_api_secret:
        raise RuntimeError("Kite API key and API secret are required.")

    _write_env_values(
        {
            "KITE_API_KEY": cleaned_api_key,
            "KITE_API_SECRET": cleaned_api_secret,
        },
        env_path,
    )
    os.environ["KITE_API_KEY"] = cleaned_api_key
    os.environ["KITE_API_SECRET"] = cleaned_api_secret


def credential_status() -> dict[str, bool]:
    load_dotenv(dotenv_path=credentials_env_path(), override=True)
    return {
        "api_key_set": bool(os.getenv("KITE_API_KEY", "").strip()),
        "api_secret_set": bool(os.getenv("KITE_API_SECRET", "").strip()),
        "access_token_set": bool(os.getenv("KITE_ACCESS_TOKEN", "").strip()),
    }


def _write_env_values(values: dict[str, str], env_path: str | Path = ".env") -> None:
    path = Path(env_path)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    updated_keys: set[str] = set()
    next_lines: list[str] = []

    for line in lines:
        key, separator, _value = line.partition("=")
        if separator and key in values:
            next_lines.append(f"{key}={values[key]}")
            updated_keys.add(key)
        else:
            next_lines.append(line)

    for key, value in values.items():
        if key not in updated_keys:
            next_lines.append(f"{key}={value}")

    path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def has_access_token() -> bool:
    try:
        return bool(load_credentials().access_token)
    except RuntimeError:
        return False
