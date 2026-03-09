import os
import yaml
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".blaqliq"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
DEFAULT_API_URL = "http://localhost:8000"


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        return {"api_url": DEFAULT_API_URL, "token": None}
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f) or {"api_url": DEFAULT_API_URL, "token": None}


def save_config(config: dict):
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def get_api_url() -> str:
    return load_config().get("api_url", DEFAULT_API_URL)


def get_token() -> Optional[str]:
    return load_config().get("token")


def set_token(token: str):
    config = load_config()
    config["token"] = token
    save_config(config)


def clear_token():
    config = load_config()
    config["token"] = None
    save_config(config)


def set_api_url(url: str):
    config = load_config()
    config["api_url"] = url
    save_config(config)
