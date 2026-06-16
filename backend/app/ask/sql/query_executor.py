from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class QueryExecutor:
    def __init__(self, session: Session, *, row_limit: int = 100, timeout_ms: int = 5000):
        self.session = session
        self.row_limit = row_limit
        self.timeout_ms = timeout_ms

    def execute(self, sql: str) -> list[dict[str, Any]]:
        limited_sql = self._with_limit(sql)
        try:
            self.session.execute(text(f"SET LOCAL statement_timeout = {int(self.timeout_ms)}"))
            rows = self.session.execute(text(limited_sql)).mappings().all()
            return [{key: self._json_value(value) for key, value in dict(row).items()} for row in rows]
        except Exception:
            self.session.rollback()
            raise

    def _with_limit(self, sql: str) -> str:
        if " limit " in f" {sql.lower()} ":
            return sql
        return f"SELECT * FROM ({sql}) ask_semantic_query LIMIT {self.row_limit}"

    def _json_value(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        return value
