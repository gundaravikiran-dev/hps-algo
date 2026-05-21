from pathlib import Path

from hps_algo.kite_client import save_access_token, save_credentials


def test_save_credentials_creates_env_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"

    save_credentials("test_key", "test_secret", env_path)

    assert env_path.read_text(encoding="utf-8") == (
        "KITE_API_KEY=test_key\n"
        "KITE_API_SECRET=test_secret\n"
    )


def test_save_credentials_preserves_other_env_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("APP_MODE=local\nKITE_API_KEY=old\n", encoding="utf-8")

    save_credentials("new_key", "new_secret", env_path)

    assert env_path.read_text(encoding="utf-8") == (
        "APP_MODE=local\n"
        "KITE_API_KEY=new_key\n"
        "KITE_API_SECRET=new_secret\n"
    )


def test_save_access_token_updates_existing_env_value(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "KITE_API_KEY=test_key\nKITE_ACCESS_TOKEN=old_token\n",
        encoding="utf-8",
    )

    save_access_token("new_token", env_path)

    assert env_path.read_text(encoding="utf-8") == (
        "KITE_API_KEY=test_key\n"
        "KITE_ACCESS_TOKEN=new_token\n"
    )
