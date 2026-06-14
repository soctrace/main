from fastapi import APIRouter, Depends

from app.schemas.metadata import VariablesMetadataResponse
from app.services.metadata_service import MetadataService, get_metadata_service


router = APIRouter()


@router.get("/variables", response_model=VariablesMetadataResponse)
def get_variables(
    metadata_service: MetadataService = Depends(get_metadata_service),
) -> VariablesMetadataResponse:
    return metadata_service.get_variables()

