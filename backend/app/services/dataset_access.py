from dataclasses import dataclass


APPROVED_MARTS = frozenset(
    {
        "marts.mv_electoral_behavior",
        "core.resultados_seccion",
        "core.election",
        "core.candidatura_alias",
        "marts.dim_seccion_display",
        "marts.v_population_layer",
        "marts.v_mapa_age_structure_2023",
        "marts.v_income_level_layer",
        "marts.v_land_built_environment",
        "marts.territorial_intelligence_section_2023",
        "marts.electoral_forecasting_municipality_2027",
        "marts.socioeconomic_intelligence_signals",
        "marts.housing_intelligence_features_2023",
        "marts.electoral_forecasting_features_2027",
        "marts.electoral_forecasting_ui_2027",
        "marts.electoral_forecast_counterweights_2027",
        "marts.electoral_scenarios_2027",
    }
)


@dataclass(frozen=True, slots=True)
class ApprovedDatasetAccess:
    """Central allow-list for analyst and forecast reads."""

    approved_marts: frozenset[str] = APPROVED_MARTS

    def require(self, *datasets: str) -> tuple[str, ...]:
        denied = sorted(set(datasets) - self.approved_marts)
        if denied:
            raise ValueError(f"Dataset is not approved for analyst access: {', '.join(denied)}")
        return datasets
