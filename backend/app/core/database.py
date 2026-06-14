from collections.abc import Generator
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()

engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def database_diagnostics() -> dict[str, str | bool | None]:
    """Return safe database connection metadata for startup logs."""
    raw_database_url = settings.database_url
    database_url_exists = bool(os.getenv("DATABASE_URL"))
    try:
        url = make_url(raw_database_url)
    except Exception:
        return {
            "database_url_exists": database_url_exists,
            "driver": None,
            "host": None,
            "database": None,
            "url_parse_error": "invalid_database_url",
        }

    return {
        "database_url_exists": database_url_exists,
        "driver": url.drivername,
        "host": url.host,
        "database": url.database,
        "url_parse_error": None,
    }


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
