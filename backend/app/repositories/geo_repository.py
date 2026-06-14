from dataclasses import dataclass
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.sql_loader import load_sql


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GeoRepository:
    session: Session

    def get_sections(
        self,
        municipality_id: str,
        year: int,
        layer: str | None = None,
        election_id: int | None = None,
    ) -> list[dict]:
        query = text(load_sql("geo_sections.sql"))
        params = {
            "municipality_id": municipality_id,
            "year": year,
            "layer": layer,
            "election_id": election_id,
        }
        try:
            result = self.session.execute(query, params)
        except SQLAlchemyError:
            logger.exception("Geo sections SQL failed", extra={"params": params})
            raise
        return [dict(row._mapping) for row in result]

    def get_sections_bbox(self, municipality_id: str, year: int) -> list[float] | None:
        query = text(load_sql("geo_sections_bbox.sql"))
        row = self.session.execute(
            query,
            {"municipality_id": municipality_id, "year": year},
        ).mappings().first()
        if not row or row["min_lon"] is None:
            return None
        return [
            float(row["min_lon"]),
            float(row["min_lat"]),
            float(row["max_lon"]),
            float(row["max_lat"]),
        ]
