from fastapi import APIRouter, Depends, Query

from app.schemas.geo import GeoFeatureCollection
from app.services.geo_service import GeoService, get_geo_service


router = APIRouter()


@router.get("/sections", response_model=GeoFeatureCollection)
def get_sections_geojson(
    municipality_id: str = Query(..., min_length=5, max_length=5),
    year: int = Query(..., ge=1900, le=2100),
    layer: str | None = Query(default=None),
    election_id: int | None = Query(default=None, ge=1),
    fields: list[str] | None = Query(default=None),
    geo_service: GeoService = Depends(get_geo_service),
) -> GeoFeatureCollection:
    return geo_service.get_sections_geojson(
        municipality_id=municipality_id,
        year=year,
        layer=layer,
        election_id=election_id,
        requested_fields=fields,
    )
