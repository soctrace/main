from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.sql_loader import load_sql


@dataclass(slots=True)
class MunicipalityRepository:
    session: Session

    def list_municipalities(self) -> list[dict]:
        query = text(load_sql("municipalities.sql"))
        result = self.session.execute(query)
        return [dict(row._mapping) for row in result]

