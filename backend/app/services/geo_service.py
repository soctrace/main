from functools import lru_cache
import logging

from fastapi import Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.repositories.geo_repository import GeoRepository
from app.schemas.geo import GeoFeature, GeoFeatureCollection, SectionFeatureProperties
from app.services.naming import district_label_from_code, municipality_name_from_id


SUPPORTED_MAP_FIELDS = {
    "section_id",
    "municipality_id",
    "municipality",
    "district",
    "section_number",
    "label_cliente",
    "section_name",
    "display_name",
    "neighborhood",
    "nombre_barrio",
    "zone",
    "label",
    "area_km2",
    "population_total",
    "population_density",
    "population_male",
    "population_female",
    "pct_male",
    "pct_female",
    "population_0_19",
    "population_0_14",
    "population_15_29",
    "population_30_44",
    "population_45_64",
    "population_65_plus",
    "dependency_ratio",
    "population_quintile",
    "density_quintile",
    "pct_65_plus",
    "average_age",
    "age_group",
    "age_group_label",
    "age_color_key",
    "over_65_pct",
    "under_30_pct",
    "density_level",
    "pct_foreign_born",
    "turnout",
    "renta_media_persona",
    "renta_media_hogar",
    "income_quintile",
    "income_level",
    "income_rank_municipal",
    "income_index",
    "income_salary",
    "income_pension",
    "income_unemployment",
    "income_social_benefits",
    "income_other",
    "pension_dependency_index",
    "employment_dependency_index",
    "welfare_dependency_index",
    "entrepreneurial_activity_signal",
    "passive_income_signal",
    "winning_party",
    "winning_party_pct",
    "runner_up_party",
    "runner_up_pct",
    "victory_margin_pct",
    "local_vote_pct",
    "national_vote_pct",
    "left_bloc_pct",
    "right_bloc_pct",
    "fragmentation_index",
    "competitive_parties_count",
    "vote_concentration_index",
    "localism_index",
    "localism_category",
    "pct_pp",
    "pct_psoe",
    "pct_vox",
    "pct_cs",
    "pct_pacma",
    "pct_por_mi_pueblo",
    "pct_soydemijas",
    "pct_a_mijas",
    "pct_adelante_andalucia",
    "pct_con_andalucia",
    "party_results_json",
    "party_vote_percentages",
    "real_estate_year",
    "num_parcelas",
    "superficie_total_parcelas_m2",
    "superficie_media_parcela_m2",
    "densidad_parcelaria",
    "num_building_parts",
    "huella_construida_m2",
    "huella_media_building_part_m2",
    "valor_catastral_estimado_m2",
    "precio_mercado_estimado_m2",
    "ratio_mercado_catastro",
    "clasificacion_inmobiliaria",
    "indice_construido",
    "urban_intensity_index",
    "urban_intensity_label",
    "urban_intensity_completeness_pct",
    "precio_m2_observado",
    "precio_m2_municipal_baseline",
    "valor_catastral_distrito_baseline",
    "market_reference_m2",
    "price_reference_is_observed",
    "market_reference_confidence_weight",
    "market_reference_type",
    "calibration_source",
    "market_pressure_index",
    "quality_life_score",
    "opportunity_signal_score",
    "opportunity_zone_score",
    "residential_saturation_index",
    "residential_balance_score",
    "urban_prestige_signal",
    "foreign_demand_exposure",
    "international_appeal_score",
    "territorial_signal_score",
    "housing_signal_score",
    "safety_potential_score",
    "noise_exposure_potential",
    "housing_stress_index",
    "daily_life_access_score",
    "quietness_potential",
    "residential_stability_proxy",
    "socioeconomic_resilience_proxy",
    "mobility_friction_proxy",
    "extreme_market_pressure",
    "market_pressure_label",
    "opportunity_label",
    "residential_profile_label",
    "prestige_label",
    "territorial_signal_label",
    "strategic_profile_label",
    "confidence_level",
    "pct_higher_studies",
    "pct_no_studies",
    "pct_secondary_studies",
    "pct_employed",
    "pct_unemployed",
    "pct_pensioner",
    "pct_self_employed",
    "pct_employee",
    "pct_services",
    "pct_construction",
    "pct_industry",
    "pct_agriculture",
    "pct_directors_managers",
    "pct_technicians_professionals",
    "pct_directors_managers_professionals",
    "pct_qualified_occupations",
    "gini_index",
    "p80_p20_ratio",
    "income_unemployment_benefits",
    "income_business_activity",
    "income_real_estate",
    "education_high_norm",
    "low_education_norm",
    "qualified_occupation_norm",
    "employment_norm",
    "unemployment_norm",
    "income_norm",
    "low_income_norm",
    "social_benefits_norm",
    "unemployment_benefits_norm",
    "ageing_pressure_norm",
    "gini_norm",
    "lower_gini_norm",
    "p80_p20_norm",
    "income_diversity_norm",
    "sector_diversity_norm",
    "professional_status_diversity_norm",
    "business_activity_norm",
    "self_employment_norm",
    "advanced_services_industry_norm",
    "income_polarization_norm",
    "balanced_age_structure_norm",
    "human_capital_index",
    "vulnerability_index",
    "resilience_index",
    "productive_complexity_index",
    "inequality_pressure_index",
    "human_capital_completeness_pct",
    "vulnerability_completeness_pct",
    "resilience_completeness_pct",
    "productive_complexity_completeness_pct",
    "inequality_pressure_completeness_pct",
    "human_capital_label",
    "vulnerability_label",
    "resilience_label",
    "productive_complexity_label",
    "inequality_pressure_label",
    "projected_leading_party",
    "projected_vote_share",
    "structural_projected_leading_party",
    "structural_projected_vote_share",
    "turnout_forecast",
    "volatility",
    "abstention_risk",
    "localist_potential",
    "swing_sections",
    "forecast_confidence",
    "structural_forecast_confidence",
    "forecast_confidence_level",
    "is_strategic_section",
    "is_swing_section",
    "is_abstention_risk_area",
    "forecast_interpretation",
    "forecast_drivers",
    "forecast_model_version",
    "oraculum_calibrated",
    "contextual_adjustment_score",
    "contextual_vote_adjustment_pct",
    "contextual_uncertainty",
    "contextual_confidence",
    "has_contextual_adjustments",
    "contextual_drivers",
}


logger = logging.getLogger(__name__)


class GeoService:
    def __init__(self, session: Session):
        self.repository = GeoRepository(session=session)

    def get_sections_geojson(
        self,
        municipality_id: str,
        year: int,
        layer: str | None,
        election_id: int | None,
        requested_fields: list[str] | None,
    ) -> GeoFeatureCollection:
        logger.info(
            "Geo sections requested",
            extra={
                "municipality_id": municipality_id,
                "year": year,
                "layer": layer,
                "election_id": election_id,
            },
        )
        try:
            rows = self.repository.get_sections(
                municipality_id=municipality_id,
                year=year,
                layer=layer,
                election_id=election_id,
            )
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=500, detail="Map data query failed") from exc
        if not rows:
            logger.warning(
                "Geo sections returned no rows",
                extra={"municipality_id": municipality_id, "year": year},
            )
            raise HTTPException(status_code=404, detail="No sections found for the query")

        selected_fields = self._normalize_fields(requested_fields)
        try:
            features = [self._build_feature(row, municipality_id, selected_fields) for row in rows]
        except (TypeError, ValueError, ValidationError) as exc:
            logger.exception(
                "Geo sections serialization failed",
                extra={"municipality_id": municipality_id, "year": year, "rows": len(rows)},
            )
            raise HTTPException(status_code=500, detail="Map data serialization failed") from exc
        bbox = self.repository.get_sections_bbox(municipality_id=municipality_id, year=year)
        logger.info(
            "Geo sections response built",
            extra={
                "municipality_id": municipality_id,
                "year": year,
                "features": len(features),
            },
        )
        return GeoFeatureCollection(features=features, bbox=bbox)

    def _normalize_fields(self, requested_fields: list[str] | None) -> set[str]:
        if not requested_fields:
            return SUPPORTED_MAP_FIELDS

        invalid_fields = sorted(set(requested_fields) - SUPPORTED_MAP_FIELDS)
        if invalid_fields:
            invalid_fields_str = ", ".join(invalid_fields)
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported fields requested: {invalid_fields_str}",
            )

        return {"section_id", "municipality_id", "municipality", "district"} | set(
            requested_fields
        )

    def _build_feature(
        self,
        row: dict,
        municipality_id: str,
        selected_fields: set[str],
    ) -> GeoFeature:
        full_properties = {
            "section_id": row["seccion_id"],
            "municipality_id": municipality_id,
            "municipality": municipality_name_from_id(municipality_id),
            "district": district_label_from_code(row["district_code"]),
            "section_number": row["seccion_numero_visible"],
            "label_cliente": row["label_cliente"],
            "section_name": row["label_cliente"] or row["nombre_barrio"],
            "display_name": row["label_cliente"] or row["nombre_barrio"] or row["seccion_numero_visible"],
            "neighborhood": row["nombre_barrio"],
            "nombre_barrio": row["nombre_barrio"],
            "zone": row["zona_macro"],
            "label": row["label_cliente"],
            "area_km2": self._to_float(row["area_km2"]),
            "population_total": row["pob_total"],
            "population_density": self._to_float(row["densidad"]),
            "population_male": row["pob_h"],
            "population_female": row["pob_m"],
            "pct_male": self._to_float(row["pct_h"]),
            "pct_female": self._to_float(row["pct_m"]),
            "population_0_19": row["pob_0_19"],
            "population_0_14": row["pob_0_14"],
            "population_15_29": row["pob_15_29"],
            "population_30_44": row["pob_30_44"],
            "population_45_64": row["pob_45_64"],
            "population_65_plus": row["pob_65p"],
            "dependency_ratio": self._to_float(row["dependency_ratio"]),
            "population_quintile": row["population_quintile"],
            "density_quintile": row["density_quintile"],
            "pct_65_plus": self._to_float(row["pct_65p"]),
            "average_age": self._to_float(row["average_age"]),
            "age_group": row["age_group"],
            "age_group_label": row["age_group_label"],
            "age_color_key": row["age_color_key"],
            "over_65_pct": self._to_float(row["over_65_pct"]),
            "under_30_pct": self._to_float(row["under_30_pct"]),
            "density_level": row["density_level"],
            "pct_foreign_born": None,
            "turnout": self._to_float(row["participacion"]),
            "renta_media_persona": self._to_float(row["renta_media_persona"]),
            "renta_media_hogar": self._to_float(row["renta_media_hogar"]),
            "income_quintile": row["income_quintile"],
            "income_level": row["income_level"],
            "income_rank_municipal": row["income_rank_municipal"],
            "income_index": self._to_float(row["income_index"]),
            "income_salary": self._to_float(row["income_salary"]),
            "income_pension": self._to_float(row["income_pension"]),
            "income_unemployment": self._to_float(row["income_unemployment"]),
            "income_social_benefits": self._to_float(row["income_social_benefits"]),
            "income_other": self._to_float(row["income_other"]),
            "pension_dependency_index": self._to_float(row["pension_dependency_index"]),
            "employment_dependency_index": self._to_float(row["employment_dependency_index"]),
            "welfare_dependency_index": self._to_float(row["welfare_dependency_index"]),
            "entrepreneurial_activity_signal": self._to_float(row["entrepreneurial_activity_signal"]),
            "passive_income_signal": self._to_float(row["passive_income_signal"]),
            "winning_party": row["sigla_ganadora"],
            "winning_party_pct": self._to_float(row["winning_party_pct"]),
            "runner_up_party": row["runner_up_party"],
            "runner_up_pct": self._to_float(row["runner_up_pct"]),
            "victory_margin_pct": self._to_float(row["victory_margin_pct"]),
            "local_vote_pct": self._to_float(row["local_vote_pct"]),
            "national_vote_pct": self._to_float(row["national_vote_pct"]),
            "left_bloc_pct": self._to_float(row["left_bloc_pct"]),
            "right_bloc_pct": self._to_float(row["right_bloc_pct"]),
            "fragmentation_index": self._to_float(row["fragmentation_index"]),
            "competitive_parties_count": row["competitive_parties_count"],
            "vote_concentration_index": self._to_float(row["vote_concentration_index"]),
            "localism_index": self._to_float(row["localism_index"]),
            "localism_category": row["localism_category"],
            "pct_pp": self._to_float(row["pct_pp"]),
            "pct_psoe": self._to_float(row["pct_psoe"]),
            "pct_vox": self._to_float(row["pct_vox"]),
            "pct_cs": self._to_float(row["pct_cs"]),
            "pct_pacma": self._to_float(row["pct_pacma"]),
            "pct_por_mi_pueblo": self._to_float(row["pct_por_mi_pueblo"]),
            "pct_soydemijas": self._to_float(row["pct_soydemijas"]),
            "pct_a_mijas": self._to_float(row["pct_a_mijas"]),
            "pct_adelante_andalucia": self._to_float(row["pct_adelante_andalucia"]),
            "pct_con_andalucia": self._to_float(row["pct_con_andalucia"]),
            "party_results_json": self._normalize_party_results(row["party_results_json"]),
            "party_vote_percentages": self._build_party_vote_percentages(row),
            "real_estate_year": row["real_estate_year"],
            "num_parcelas": row["num_parcelas"],
            "superficie_total_parcelas_m2": self._to_float(row["superficie_total_parcelas_m2"]),
            "superficie_media_parcela_m2": self._to_float(row["superficie_media_parcela_m2"]),
            "densidad_parcelaria": self._to_float(row["densidad_parcelaria"]),
            "num_building_parts": row["num_building_parts"],
            "huella_construida_m2": self._to_float(row["huella_construida_m2"]),
            "huella_media_building_part_m2": self._to_float(row["huella_media_building_part_m2"]),
            "valor_catastral_estimado_m2": self._to_float(row["valor_catastral_estimado_m2"]),
            "precio_mercado_estimado_m2": self._to_float(row["precio_mercado_estimado_m2"]),
            "ratio_mercado_catastro": self._to_float(row["ratio_mercado_catastro"]),
            "clasificacion_inmobiliaria": row["clasificacion_inmobiliaria"],
            "indice_construido": self._to_float(row["indice_construido"]),
            "urban_intensity_index": self._to_float(row["urban_intensity_index"]),
            "urban_intensity_label": row["urban_intensity_label"],
            "urban_intensity_completeness_pct": self._to_float(row["urban_intensity_completeness_pct"]),
            "precio_m2_observado": self._to_float(row["precio_m2_observado"]),
            "precio_m2_municipal_baseline": self._to_float(row["precio_m2_municipal_baseline"]),
            "valor_catastral_distrito_baseline": self._to_float(row["valor_catastral_distrito_baseline"]),
            "market_reference_m2": self._to_float(row["market_reference_m2"]),
            "price_reference_is_observed": row["price_reference_is_observed"],
            "market_reference_confidence_weight": self._to_float(row["market_reference_confidence_weight"]),
            "market_reference_type": row["market_reference_type"],
            "calibration_source": row["calibration_source"],
            "market_pressure_index": self._to_float(row["market_pressure_index"]),
            "quality_life_score": self._to_float(row["quality_life_score"]),
            "opportunity_signal_score": self._to_float(row["opportunity_signal_score"]),
            "opportunity_zone_score": self._to_float(row["opportunity_zone_score"]),
            "residential_saturation_index": self._to_float(row["residential_saturation_index"]),
            "residential_balance_score": self._to_float(row["residential_balance_score"]),
            "urban_prestige_signal": self._to_float(row["urban_prestige_signal"]),
            "foreign_demand_exposure": self._to_float(row["foreign_demand_exposure"]),
            "international_appeal_score": self._to_float(row["international_appeal_score"]),
            "territorial_signal_score": self._to_float(row["territorial_signal_score"]),
            "housing_signal_score": self._to_float(row["housing_signal_score"]),
            "safety_potential_score": self._to_float(row["safety_potential_score"]),
            "noise_exposure_potential": self._to_float(row["noise_exposure_potential"]),
            "housing_stress_index": self._to_float(row["housing_stress_index"]),
            "daily_life_access_score": self._to_float(row["daily_life_access_score"]),
            "quietness_potential": self._to_float(row["quietness_potential"]),
            "residential_stability_proxy": self._to_float(row["residential_stability_proxy"]),
            "socioeconomic_resilience_proxy": self._to_float(row["socioeconomic_resilience_proxy"]),
            "mobility_friction_proxy": self._to_float(row["mobility_friction_proxy"]),
            "extreme_market_pressure": self._to_float(row["extreme_market_pressure"]),
            "market_pressure_label": row["market_pressure_label"],
            "opportunity_label": row["opportunity_label"],
            "residential_profile_label": row["residential_profile_label"],
            "prestige_label": row["prestige_label"],
            "territorial_signal_label": row["territorial_signal_label"],
            "strategic_profile_label": row["strategic_profile_label"],
            "confidence_level": row["confidence_level"],
            "pct_higher_studies": self._to_float(row["pct_higher_studies"]),
            "pct_no_studies": self._to_float(row["pct_no_studies"]),
            "pct_secondary_studies": self._to_float(row["pct_secondary_studies"]),
            "pct_employed": self._to_float(row["pct_employed"]),
            "pct_unemployed": self._to_float(row["pct_unemployed"]),
            "pct_pensioner": self._to_float(row["pct_pensioner"]),
            "pct_self_employed": self._to_float(row["pct_self_employed"]),
            "pct_employee": self._to_float(row["pct_employee"]),
            "pct_services": self._to_float(row["pct_services"]),
            "pct_construction": self._to_float(row["pct_construction"]),
            "pct_industry": self._to_float(row["pct_industry"]),
            "pct_agriculture": self._to_float(row["pct_agriculture"]),
            "pct_directors_managers": self._to_float(row["pct_directors_managers"]),
            "pct_technicians_professionals": self._to_float(row["pct_technicians_professionals"]),
            "pct_directors_managers_professionals": self._to_float(row["pct_directors_managers_professionals"]),
            "pct_qualified_occupations": self._to_float(row["pct_qualified_occupations"]),
            "gini_index": self._to_float(row["gini_index"]),
            "p80_p20_ratio": self._to_float(row["p80_p20_ratio"]),
            "income_unemployment_benefits": self._to_float(row["income_unemployment_benefits"]),
            "income_business_activity": self._to_float(row["income_business_activity"]),
            "income_real_estate": self._to_float(row["income_real_estate"]),
            "education_high_norm": self._to_float(row["education_high_norm"]),
            "low_education_norm": self._to_float(row["low_education_norm"]),
            "qualified_occupation_norm": self._to_float(row["qualified_occupation_norm"]),
            "employment_norm": self._to_float(row["employment_norm"]),
            "unemployment_norm": self._to_float(row["unemployment_norm"]),
            "income_norm": self._to_float(row["income_norm"]),
            "low_income_norm": self._to_float(row["low_income_norm"]),
            "social_benefits_norm": self._to_float(row["social_benefits_norm"]),
            "unemployment_benefits_norm": self._to_float(row["unemployment_benefits_norm"]),
            "ageing_pressure_norm": self._to_float(row["ageing_pressure_norm"]),
            "gini_norm": self._to_float(row["gini_norm"]),
            "lower_gini_norm": self._to_float(row["lower_gini_norm"]),
            "p80_p20_norm": self._to_float(row["p80_p20_norm"]),
            "income_diversity_norm": self._to_float(row["income_diversity_norm"]),
            "sector_diversity_norm": self._to_float(row["sector_diversity_norm"]),
            "professional_status_diversity_norm": self._to_float(row["professional_status_diversity_norm"]),
            "business_activity_norm": self._to_float(row["business_activity_norm"]),
            "self_employment_norm": self._to_float(row["self_employment_norm"]),
            "advanced_services_industry_norm": self._to_float(row["advanced_services_industry_norm"]),
            "income_polarization_norm": self._to_float(row["income_polarization_norm"]),
            "balanced_age_structure_norm": self._to_float(row["balanced_age_structure_norm"]),
            "human_capital_index": self._to_float(row["human_capital_index"]),
            "vulnerability_index": self._to_float(row["vulnerability_index"]),
            "resilience_index": self._to_float(row["resilience_index"]),
            "productive_complexity_index": self._to_float(row["productive_complexity_index"]),
            "inequality_pressure_index": self._to_float(row["inequality_pressure_index"]),
            "human_capital_completeness_pct": self._to_float(row["human_capital_completeness_pct"]),
            "vulnerability_completeness_pct": self._to_float(row["vulnerability_completeness_pct"]),
            "resilience_completeness_pct": self._to_float(row["resilience_completeness_pct"]),
            "productive_complexity_completeness_pct": self._to_float(row["productive_complexity_completeness_pct"]),
            "inequality_pressure_completeness_pct": self._to_float(row["inequality_pressure_completeness_pct"]),
            "human_capital_label": row["human_capital_label"],
            "vulnerability_label": row["vulnerability_label"],
            "resilience_label": row["resilience_label"],
            "productive_complexity_label": row["productive_complexity_label"],
            "inequality_pressure_label": row["inequality_pressure_label"],
            "projected_leading_party": row["projected_leading_party"],
            "projected_vote_share": self._to_float(row["projected_vote_share"]),
            "structural_projected_leading_party": row["structural_projected_leading_party"],
            "structural_projected_vote_share": self._to_float(row["structural_projected_vote_share"]),
            "turnout_forecast": self._to_float(row["turnout_forecast"]),
            "volatility": self._to_float(row["volatility"]),
            "abstention_risk": self._to_float(row["abstention_risk"]),
            "localist_potential": self._to_float(row["localist_potential"]),
            "swing_sections": self._to_float(row["swing_sections"]),
            "forecast_confidence": self._to_float(row["forecast_confidence"]),
            "structural_forecast_confidence": self._to_float(row["structural_forecast_confidence"]),
            "forecast_confidence_level": row["forecast_confidence_level"],
            "is_strategic_section": row["is_strategic_section"],
            "is_swing_section": row["is_swing_section"],
            "is_abstention_risk_area": row["is_abstention_risk_area"],
            "forecast_interpretation": row["forecast_interpretation"],
            "forecast_drivers": row["forecast_drivers"] or [],
            "forecast_model_version": row["forecast_model_version"],
            "oraculum_calibrated": row["oraculum_calibrated"],
            "contextual_adjustment_score": self._to_float(row["contextual_adjustment_score"]),
            "contextual_vote_adjustment_pct": self._to_float(row["contextual_vote_adjustment_pct"]),
            "contextual_uncertainty": self._to_float(row["contextual_uncertainty"]),
            "contextual_confidence": row["contextual_confidence"],
            "has_contextual_adjustments": row["has_contextual_adjustments"],
            "contextual_drivers": row["contextual_drivers"] or [],
        }
        filtered_properties = {
            key: value for key, value in full_properties.items() if key in selected_fields
        }
        return GeoFeature(
            geometry=row["geometry"],
            properties=SectionFeatureProperties.model_validate(filtered_properties),
        )

    @staticmethod
    def _to_float(value) -> float | None:
        return float(value) if value is not None else None

    def _build_party_vote_percentages(self, row: dict) -> list[dict[str, float | str]]:
        party_results = self._normalize_party_results(row.get("party_results_json"))
        if party_results:
            return [
                {
                    "party": result["party"],
                    "percentage": self._as_percent_points(result["pct"]) or 0,
                }
                for result in party_results
                if result.get("party") is not None and result.get("pct") is not None
            ]

        percentages = [
            ("PP", self._as_percent_points(row["pct_pp"])),
            ("PSOE", self._as_percent_points(row["pct_psoe"])),
            ("VOX", self._as_percent_points(row["pct_vox"])),
        ]
        return [
            {"party": party, "percentage": round(percentage, 1)}
            for party, percentage in sorted(
                ((party, percentage) for party, percentage in percentages if percentage is not None),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

    def _as_percent_points(self, value) -> float | None:
        numeric_value = self._to_float(value)
        if numeric_value is None:
            return None
        return numeric_value * 100 if numeric_value <= 1 else numeric_value

    def _normalize_party_results(self, value) -> list[dict]:
        if not value:
            return []
        if not isinstance(value, list):
            logger.warning("Unexpected party_results_json shape", extra={"type": type(value).__name__})
            return []

        normalized = []
        for item in value:
            if not isinstance(item, dict):
                continue
            party = item.get("party")
            pct = self._to_float(item.get("pct"))
            votes = item.get("votes") or 0
            if party is None or pct is None:
                continue
            normalized.append({"party": party, "pct": pct, "votes": int(votes)})
        return normalized


def get_geo_service(session: Session = Depends(get_db_session)) -> GeoService:
    return GeoService(session=session)
