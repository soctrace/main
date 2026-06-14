from fastapi import APIRouter, Depends, Path

from app.schemas.forecast import (
    ForecastMunicipalityOutlook,
    ForecastScenario,
    ForecastScenarioList,
    ForecastSectionOutlook,
)
from app.services.forecast_service import ForecastService, get_forecast_service


router = APIRouter()


@router.get("/municipalities/{municipality_id}/elections/2027", response_model=ForecastMunicipalityOutlook)
def get_municipality_forecast(
    municipality_id: str = Path(..., min_length=5, max_length=5),
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> ForecastMunicipalityOutlook:
    return forecast_service.get_municipality_outlook(municipality_id)


@router.get("/sections/{section_id}/elections/2027", response_model=ForecastSectionOutlook)
def get_section_forecast(
    section_id: str = Path(..., min_length=10, max_length=10),
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> ForecastSectionOutlook:
    return forecast_service.get_section_outlook(section_id)


@router.get("/mijas/2027/scenarios", response_model=ForecastScenarioList)
def get_mijas_forecast_scenarios(
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> ForecastScenarioList:
    return forecast_service.get_scenarios("29070")


@router.get("/mijas/2027/scenarios/{scenario_id}", response_model=ForecastScenario)
def get_mijas_forecast_scenario(
    scenario_id: str = Path(
        ...,
        pattern="^(structural|candidate_reset|localist_fragmentation|oraculum_ready)$",
    ),
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> ForecastScenario:
    return forecast_service.get_scenario("29070", scenario_id)
