from __future__ import annotations

from pathlib import Path
import os

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yml"


def load_settings() -> dict:
    if not DEFAULT_SETTINGS_PATH.exists():
        return {}

    with DEFAULT_SETTINGS_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data


def get_database_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    settings = load_settings()
    db_name = settings.get("project", {}).get("database", "mijas")
    return f"postgresql:///{db_name}"


def get_project_name() -> str:
    settings = load_settings()
    return settings.get("project", {}).get("name", "soctrace")
