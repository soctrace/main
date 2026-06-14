from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.repositories.municipality_repository import MunicipalityRepository
from app.schemas.municipality import MunicipalityListResponse, MunicipalitySummary
from app.services.naming import municipality_name_from_id


class MunicipalityService:
    def __init__(self, session: Session):
        self.repository = MunicipalityRepository(session=session)

    def list_municipalities(self) -> MunicipalityListResponse:
        items = []
        for row in self.repository.list_municipalities():
            available_years = [
                int(year)
                for year in (row.get("available_years") or [])
                if year is not None
            ]
            municipality_id = row["municipality_id"]
            items.append(
                MunicipalitySummary(
                    municipality_id=municipality_id,
                    name=municipality_name_from_id(municipality_id),
                    section_count=int(row["section_count"]),
                    available_years=available_years,
                )
            )
        return MunicipalityListResponse(items=items)


def get_municipality_service(
    session: Session = Depends(get_db_session),
) -> MunicipalityService:
    return MunicipalityService(session=session)

