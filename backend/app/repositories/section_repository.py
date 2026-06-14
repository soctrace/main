from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.sql_loader import load_sql


@dataclass(slots=True)
class SectionRepository:
    session: Session

    def get_section_detail(
        self,
        section_id: str,
        year: int,
        election_id: int | None = None,
    ) -> dict | None:
        query = text(load_sql("section_detail.sql"))
        row = self.session.execute(
            query,
            {
                "section_id": section_id,
                "year": year,
                "election_id": election_id,
            },
        ).mappings().first()
        return dict(row) if row else None
