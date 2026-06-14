from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.repositories.forecast_repository import ForecastRepository
from app.schemas.forecast import (
    ForecastMunicipalityOutlook,
    ForecastScenario,
    ForecastScenarioList,
    ForecastSectionOutlook,
)
from app.services.dataset_access import ApprovedDatasetAccess


FORECAST_VARIABLES = [
    "turnout_forecast",
    "volatility",
    "abstention_risk",
    "localist_potential",
    "swing_sections",
    "forecast_confidence",
    "contextual_vote_adjustment_pct",
    "contextual_uncertainty",
]


class ForecastService:
    def __init__(self, session: Session):
        self.repository = ForecastRepository(session=session)
        self.datasets = ApprovedDatasetAccess()

    def get_municipality_outlook(self, municipality_id: str) -> ForecastMunicipalityOutlook:
        self.datasets.require(
            "marts.electoral_forecasting_features_2027",
            "marts.electoral_forecasting_municipality_2027",
            "marts.electoral_forecast_counterweights_2027",
        )
        row = self.repository.get_municipality_outlook(municipality_id)
        if not row:
            raise HTTPException(status_code=404, detail="Municipality forecast not found")
        outlook = ForecastMunicipalityOutlook(**row)
        self.repository.audit(
            question=f"Forecast outlook for municipality {municipality_id}",
            municipality_id=municipality_id,
            section_id=None,
            confidence_level=outlook.confidence_level,
            variables_used=FORECAST_VARIABLES,
            metadata={"forecast_year": 2027, "oraculum_calibrated": outlook.oraculum_calibrated},
        )
        return outlook

    def get_section_outlook(self, section_id: str) -> ForecastSectionOutlook:
        self.datasets.require(
            "marts.electoral_forecasting_features_2027",
            "marts.electoral_forecasting_ui_2027",
            "marts.electoral_forecast_counterweights_2027",
        )
        row = self.repository.get_section_outlook(section_id)
        if not row:
            raise HTTPException(status_code=404, detail="Section forecast not found")
        row["section_id"] = row.pop("seccion_id")
        outlook = ForecastSectionOutlook(**row)
        self.repository.audit(
            question=f"Forecast outlook for section {section_id}",
            municipality_id=outlook.municipality_id,
            section_id=section_id,
            confidence_level=outlook.confidence_level,
            variables_used=FORECAST_VARIABLES,
            metadata={"forecast_year": 2027, "oraculum_calibrated": outlook.oraculum_calibrated},
        )
        return outlook

    def get_scenarios(self, municipality_id: str) -> ForecastScenarioList:
        self.datasets.require(
            "marts.electoral_forecasting_municipality_2027",
            "marts.electoral_forecast_counterweights_2027",
            "marts.electoral_scenarios_2027",
        )
        scenarios = [ForecastScenario(**row) for row in self.repository.get_scenarios(municipality_id)]
        if not scenarios:
            raise HTTPException(status_code=404, detail="Municipality forecast scenarios not found")
        self.repository.audit(
            question=f"Forecast scenarios for municipality {municipality_id}",
            municipality_id=municipality_id,
            section_id=None,
            confidence_level="scenario_comparison",
            variables_used=FORECAST_VARIABLES + ["electoral_supply_uncertainty"],
            metadata={"forecast_year": 2027, "scenario_ids": [item.scenario_id for item in scenarios]},
        )
        return ForecastScenarioList(municipality_id=municipality_id, scenarios=scenarios)

    def get_scenario(self, municipality_id: str, scenario_id: str) -> ForecastScenario:
        self.datasets.require(
            "marts.electoral_forecasting_municipality_2027",
            "marts.electoral_forecast_counterweights_2027",
            "marts.electoral_scenarios_2027",
        )
        row = self.repository.get_scenario(municipality_id, scenario_id)
        if not row:
            raise HTTPException(status_code=404, detail="Municipality forecast scenario not found")
        scenario = ForecastScenario(**row)
        self.repository.audit(
            question=f"Forecast scenario {scenario_id} for municipality {municipality_id}",
            municipality_id=municipality_id,
            section_id=None,
            confidence_level="scenario_comparison",
            variables_used=FORECAST_VARIABLES + ["electoral_supply_uncertainty"],
            metadata={"forecast_year": 2027, "scenario_id": scenario_id},
        )
        return scenario


def get_forecast_service(session: Session = Depends(get_db_session)) -> ForecastService:
    return ForecastService(session=session)
