from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.repositories.analyst_repository import AnalystRepository


router = APIRouter()


@router.get("/results-normalized")
def get_normalized_election_results(
    municipality: str = Query("29070", description="Municipality id. Mijas is 29070."),
    party: str | None = Query(None),
    section_id: str | None = Query(None),
    election_type: str | None = Query(None),
    year: int | None = Query(None),
    session: Session = Depends(get_db_session),
) -> list[dict]:
    repository = AnalystRepository(session)
    municipality_id = "29070" if municipality.strip().lower() == "mijas" else municipality
    return repository.get_normalized_election_results(
        municipality_id=municipality_id,
        party=party.upper() if party else None,
        section_id=section_id,
        election_type=election_type,
        year=year,
    )
