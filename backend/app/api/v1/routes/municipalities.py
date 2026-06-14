from fastapi import APIRouter, Depends

from app.schemas.municipality import MunicipalityListResponse
from app.services.municipality_service import (
    MunicipalityService,
    get_municipality_service,
)


router = APIRouter()


@router.get("", response_model=MunicipalityListResponse)
def get_municipalities(
    municipality_service: MunicipalityService = Depends(get_municipality_service),
) -> MunicipalityListResponse:
    return municipality_service.list_municipalities()

