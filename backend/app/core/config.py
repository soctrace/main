from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SocTrace API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(default="postgresql+psycopg:///mijas")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"]
    )
    llm_provider: str = "mock"
    gemini_api_key: str | None = None
    gemini_fast_model: str = "gemini-2.5-flash-lite"
    gemini_default_model: str = "gemini-2.5-flash"
    gemini_pro_model: str = "gemini-2.5-pro"
    gemini_timeout_seconds: float = 20.0
    gemini_max_output_tokens: int = 1200
    gemini_temperature: float = 0.2
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_default_model: str = "gpt-4.1-mini"
    openai_pro_model: str = "gpt-4.1"
    openai_timeout_seconds: float = 20.0
    ask_max_tool_calls: int = 4
    ask_debug_enabled: bool = False
    ask_use_llm_planner: bool = False
    ask_llm_provider: str | None = None
    ask_llm_max_planning_attempts: int = 2
    ask_llm_require_tool_for_numeric: bool = True
    ask_llm_fallback_to_semantic_v2: bool = True
    ask_llm_fallback_to_legacy: bool = True
    ask_llm_debug: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    demo_request_to_email: str = "soctrace@gmail.com"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.database_url != "postgresql+psycopg:///mijas":
        return settings

    project_root = Path(__file__).resolve().parents[3]
    settings_path = project_root / "config" / "settings.yml"
    if not settings_path.exists():
        return settings

    with settings_path.open("r", encoding="utf-8") as settings_file:
        yaml_data = yaml.safe_load(settings_file) or {}

    database_name = yaml_data.get("project", {}).get("database")
    if not database_name:
        return settings

    return settings.model_copy(
        update={"database_url": f"postgresql+psycopg:///{database_name}"}
    )
