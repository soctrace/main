from functools import lru_cache
from pathlib import Path


SQL_DIR = Path(__file__).resolve().parents[1] / "db" / "sql"


@lru_cache
def load_sql(filename: str) -> str:
    return (SQL_DIR / filename).read_text(encoding="utf-8")

