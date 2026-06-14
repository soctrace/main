from fastapi import APIRouter, Depends, Path, Query

from app.schemas.section import SectionDetailResponse
from app.services.section_service import SectionService, get_section_service


router = APIRouter()


@router.get("/{section_id}", response_model=SectionDetailResponse)
def get_section_detail(
    section_id: str = Path(..., min_length=10, max_length=10),
    year: int = Query(default=2023, ge=1900, le=2100),
    election_id: int | None = Query(default=None, ge=1),
    section_service: SectionService = Depends(get_section_service),
) -> SectionDetailResponse:
    return section_service.get_section_detail(section_id, year=year, election_id=election_id)
