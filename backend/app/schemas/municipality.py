from pydantic import BaseModel


class MunicipalitySummary(BaseModel):
    municipality_id: str
    name: str
    section_count: int
    available_years: list[int]


class MunicipalityListResponse(BaseModel):
    items: list[MunicipalitySummary]

