from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ask.semantic_layer import SemanticCatalog, SemanticOperationInterpreter
from app.ask.sql import SqlGenerator, SqlValidator


APPROVED_VIEWS: dict[str, set[str]] = {
    "marts.agent_section_lookup": {"municipio_id", "municipio_nombre", "section_id", "section_number", "section_name", "display_name"},
    "marts.agent_population_age": {"municipio_id", "municipio_nombre", "section_id", "section_name", "year", "gender", "age_cohort", "age_min", "age_max", "people"},
    "marts.agent_section_profile": {"municipio_id", "municipio_nombre", "section_id", "section_name", "year", "population_total", "population_density", "average_age", "population_under_18", "population_under_18_pct", "population_under_30", "population_under_30_pct", "population_over_65", "population_over_65_pct", "income_individual", "income_household", "participation_pct", "abstention_pct", "winner_party", "built_footprint", "parcel_density", "building_intensity", "estimated_real_estate_value_m2", "market_price_estimated_m2", "housing_pressure_label"},
    "marts.agent_electoral_results": {"municipio_id", "municipio_nombre", "section_id", "section_name", "election_id", "election_type", "election_year", "election_month", "election_label", "party", "canonical_party", "votes", "valid_votes", "vote_pct"},
    "marts.agent_electoral_summary": {"municipio_id", "municipio_nombre", "section_id", "section_name", "election_id", "election_type", "election_year", "election_label", "census", "valid_votes", "total_votes", "participation_pct", "abstention_pct", "winner_party", "winner_vote_pct", "second_party", "second_vote_pct", "margin_pct"},
    "marts.agent_income_sources": {"municipio_id", "municipio_nombre", "section_id", "section_name", "year", "income_individual", "income_household", "salary_share", "pension_share", "unemployment_share", "other_income_share"},
    "marts.agent_housing_profile": {"municipio_id", "municipio_nombre", "section_id", "section_name", "year", "parcel_density", "built_footprint", "avg_plot_size", "building_intensity", "estimated_cadastral_value_m2", "market_price_estimated_m2", "market_to_cadastral_ratio", "housing_classification", "residential_pressure_index"},
}

IMPLEMENTED_OPERATIONS = {
    "rank_sections",
    "aggregate_municipality",
    "compare_years",
    "filter_sections",
    "party_strength",
    "persistent_winner",
    "historical_party_average",
    "age_cohort_projection",
    "population_growth",
    "cross_metric_ranking",
    "correlation_analysis",
}

TEST_QUESTIONS = [
    "¿Cuál es la sección con mayor población?",
    "¿Cuál es la sección con menor población?",
    "¿Qué secciones superan los 5.000 habitantes?",
    "¿Cuál es la población total de Mijas?",
    "¿Qué zonas han crecido más?",
    "¿Cuál es la sección más joven?",
    "¿Cuál es la sección más envejecida?",
    "¿Qué secciones concentran más población joven?",
    "¿Qué secciones concentran más jubilados?",
    "¿Qué sección ha rejuvenecido más desde 2021?",
    "¿Qué sección ha envejecido más desde 2021?",
    "¿Cuántas personas aproximadamente tendrán 18 años en 2027?",
    "¿Qué secciones tendrán más nuevos votantes en 2027?",
    "¿Cuántas personas tenían entre 18 y 22 años en 2023?",
    "¿Dónde gana siempre el PP?",
    "¿Dónde gana siempre el PSOE?",
    "¿Dónde es más fuerte el PP?",
    "¿Qué sección tiene más abstención?",
    "¿Qué sección tiene más participación?",
    "¿Cuáles son las secciones más disputadas?",
    "¿Cuál es la sección más rica?",
    "¿Cuál es la sección más pobre?",
    "¿Qué secciones tienen mayor peso de pensiones?",
    "¿Qué secciones tienen mayor valor inmobiliario?",
    "¿Qué zonas tienen mayor presión residencial?",
    "¿Qué zonas tienen mayor intensidad construida?",
    "¿Qué secciones combinan renta baja y alta abstención?",
    "¿Qué zonas tienen más jóvenes y menos renta?",
    "¿Qué secciones combinan renta alta y voto al PP?",
]


@dataclass(frozen=True)
class Check:
    ok: bool
    message: str


def icon(check: Check) -> str:
    return "OK" if check.ok else "FAIL"


def check_catalog_shape(raw: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    checks.append(Check(raw.get("version") == 2, "catalog version is 2"))
    for key in ("entities", "views", "metrics", "operations", "intent_patterns", "unsupported"):
        checks.append(Check(isinstance(raw.get(key), dict), f"catalog has {key}"))
    checks.append(Check("approved_views" not in raw and "approved_metrics" not in raw, "legacy approved_* blocks removed"))
    return checks


def check_views(raw: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    sources = [view.get("source") for view in raw.get("views", {}).values()]
    checks.append(Check(set(sources) == set(APPROVED_VIEWS), "views are exactly the approved agent_* relations"))
    checks.append(Check(not any(".ask_" in str(source) for source in sources), "no v2 view points to marts.ask_*"))
    return checks


def check_metrics(catalog: SemanticCatalog) -> list[Check]:
    checks: list[Check] = []
    for metric in catalog.metrics.values():
        checks.append(Check(metric.view in APPROVED_VIEWS, f"{metric.metric_id} uses approved view {metric.view}"))
        checks.append(Check(".ask_" not in metric.view, f"{metric.metric_id} does not use marts.ask_*"))
        checks.append(Check(metric.field in APPROVED_VIEWS.get(metric.view, set()), f"{metric.metric_id}.{metric.field} exists in {metric.view}"))
        checks.append(Check(isinstance(metric.synonyms_es, tuple), f"{metric.metric_id} Spanish synonyms are a list"))
        checks.append(Check(isinstance(metric.synonyms_en, tuple), f"{metric.metric_id} English synonyms are a list"))
    return checks


def check_operations(raw: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    for operation in raw.get("operations", {}):
        if operation in {"filter_sections", "section_profile"}:
            checks.append(Check(True, f"{operation} is cataloged for v2 but not exposed as supported MVP"))
        else:
            checks.append(Check(operation in IMPLEMENTED_OPERATIONS, f"{operation} references implemented code"))
    return checks


def check_test_questions() -> list[Check]:
    generator = SqlGenerator()
    validator = SqlValidator(generator.approved_relations)
    interpreter = SemanticOperationInterpreter(generator.semantic_catalog)
    checks: list[Check] = []
    for question in TEST_QUESTIONS:
        operation = interpreter.interpret(question, municipio_id="29070")
        plan = generator.generate(question, active_municipality="29070")
        if operation and operation.operation in IMPLEMENTED_OPERATIONS and plan:
            checks.append(Check(validator.validate(plan.sql).ok, f"{question} maps to supported SQL"))
        elif operation and operation.operation in {"cross_metric_ranking"}:
            checks.append(Check(True, f"{question} maps to beta operation"))
        else:
            checks.append(Check(False, f"{question} did not map to supported or beta operation"))
    return checks


def main() -> int:
    catalog = SemanticCatalog()
    raw = yaml.safe_load(catalog.path.read_text(encoding="utf-8"))
    checks = (
        check_catalog_shape(raw)
        + check_views(raw)
        + check_metrics(catalog)
        + check_operations(raw)
        + check_test_questions()
    )
    for check in checks:
        print(f"{icon(check)} {check.message}")
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
