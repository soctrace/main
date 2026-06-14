from dataclasses import dataclass
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.sql_loader import load_sql


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MunicipalityRepository:
    session: Session

    def list_municipalities(self) -> list[dict]:
        query = text(load_sql("municipalities.sql"))
        try:
            result = self.session.execute(query)
        except SQLAlchemyError:
            logger.exception("Municipalities SQL failed")
            raise
        return [dict(row._mapping) for row in result]
