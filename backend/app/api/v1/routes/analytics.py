from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ask.tools import build_tool_registry
from app.core.database import get_db_session


router = APIRouter()


@router.get("/age-cohort-abstention-by-section")
def age_cohort_abstention_by_section(
    municipality: str = Query(default="Mijas"),
    year: int = Query(default=2023),
    election_type: Literal["municipales", "andaluzas", "congreso", "europeas"] = Query(default="municipales"),
    min_age: int = Query(default=18, ge=0),
    max_age: int | None = Query(default=22, ge=0),
    session: Session = Depends(get_db_session),
) -> dict:
    registry = build_tool_registry(session)
    result = registry.execute(
        "age_cohort_abstention_by_section",
        {
            "municipality": municipality,
            "year": year,
            "electionType": election_type,
            "minAge": min_age,
            "maxAge": max_age,
            "groupBy": "section",
            "sortBy": "estimated_abstainers",
            "sortDirection": "desc",
        },
    )
    return result["result"] if result.get("ok") else result
