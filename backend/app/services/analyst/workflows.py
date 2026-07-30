from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from app.services.analyst.planner import PoliticalPlan
from app.services.analyst.tools import AnalystToolResult, PoliticalAnalystTools


EVIDENCE_FIELDS = [
    "section_id",
    "section_name",
    "population_total",
    "winning_party",
    "winning_party_pct",
    "runner_up_pct",
    "victory_margin_pct",
    "target_party_vote_pct",
    "abstention_rate_pct",
    "population_growth_pct",
    "avg_age",
    "income",
    "opportunity_score",
    "strategic_label",
    "reason",
    "population_density",
    "under_30_pct",
    "over_65_pct",
    "urban_intensity_index",
    "labor_training_score",
    "productive_complexity_index",
    "productive_complexity_label",
    "vulnerability_index",
    "human_capital_index",
    "resilience_index",
    "employment_norm",
    "unemployment_norm",
    "qualified_occupation_norm",
    "low_education_norm",
    "pct_employed",
    "pct_unemployed",
    "pct_qualified_occupations",
    "target_audience_reason",
    "recommended_channel",
    "recommended_action",
    "data_support",
]


@dataclass(slots=True)
class WorkflowOutput:
    tool_result: AnalystToolResult
    tool_names: list[str] = field(default_factory=list)
    plan: PoliticalPlan | None = None


class PoliticalAnalystWorkflowExecutor:
    def __init__(self, tools: PoliticalAnalystTools):
        self.tools = tools

    def run(self, plan: PoliticalPlan, year: int = 2023) -> WorkflowOutput:
        if plan.goal == "population_max_section":
            result = self.tools.get_population_ranking(plan.municipality_id, year=year, limit=1)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if plan.goal == "elderly_population_max_section":
            result = self.tools.get_elderly_population_ranking(plan.municipality_id, year=year, limit=1)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if plan.goal == "population_change_between_years":
            start_year, end_year = _plan_years(plan, fallback_end_year=year)
            result = self.tools.get_population_change_ranking(plan.municipality_id, start_year=start_year, end_year=end_year, limit=8)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if plan.goal == "electoral_change_between_years":
            start_year, end_year = _plan_years(plan, fallback_end_year=year)
            result = self.tools.get_electoral_change_ranking(plan.municipality_id, start_year=start_year, end_year=end_year, limit=8)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if plan.goal == "income_change_between_years":
            start_year, end_year = _plan_years(plan, fallback_end_year=year)
            result = self.tools.get_income_change_ranking(plan.municipality_id, start_year=start_year, end_year=end_year, limit=8)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if plan.goal == "campaign_plan":
            return self._campaign_plan(plan, year)
        if plan.goal == "candidate_visit_plan":
            return self._candidate_visit_plan(plan, year)
        if plan.goal == "abstention_analysis":
            return self._abstention_analysis(plan, year)
        if plan.goal == "party_growth_opportunity":
            return self._party_growth_opportunity(plan, year)
        if plan.goal in {
            "territorial_marketing",
            "service_launch",
            "commercial_targeting",
            "demographic_targeting",
        }:
            return self._territorial_marketing(plan, year)
        if plan.goal == "public_service_outreach":
            return self._public_service_outreach(plan, year)
        if plan.goal == "labor_training_outreach":
            return self._labor_training_outreach(plan, year)
        if plan.goal == "sports_facilities_planning":
            return self._sports_facilities_planning(plan, year)
        if plan.goal == "real_estate_location_advice":
            return self._real_estate_location_advice(plan, year)
        if plan.goal in {"urban_planning", "socioeconomic_analysis", "general_territorial_advice"}:
            return self._general_territorial_advice(plan, year)
        if plan.goal in {"mobilization_strategy", "persuasion_strategy", "territorial_prioritization"}:
            return self._campaign_plan(plan, year)
        return WorkflowOutput(
            tool_result=AnalystToolResult(
                name=plan.goal,
                rows=[],
                data_used=[],
                methodology="El planificador no necesita un flujo estrategico compuesto para esta pregunta.",
                warnings=[],
            ),
            tool_names=[],
            plan=plan,
        )

    def _campaign_plan(self, plan: PoliticalPlan, year: int) -> WorkflowOutput:
        party = plan.target_party or "PP"
        collected = self._collect(
            [
                ("get_election_results", lambda: self.tools.get_election_results(plan.municipality_id, party=plan.target_party, year=year, limit=12)),
                ("get_turnout_analysis", lambda: self.tools.get_turnout_analysis(plan.municipality_id, year=year, limit=12)),
                ("get_population_trend", lambda: self.tools.get_population_trend(plan.municipality_id, year=year, limit=12)),
                ("get_age_structure", lambda: self.tools.get_age_structure(plan.municipality_id, limit=12, youngest=True)),
                ("get_income_profile", lambda: self.tools.get_income_profile(plan.municipality_id, year=year, limit=12)),
                ("rank_sections_by_opportunity", lambda: self.tools.rank_sections_by_opportunity(plan.municipality_id, target_party=party, year=year, limit=10)),
                ("build_campaign_recommendation", lambda: self.tools.build_campaign_recommendation(plan.municipality_id, target_party=party, year=year)),
            ]
        )
        rows = _merge_evidence(collected.results, mode="campaign_plan", target_party=plan.target_party)
        methodology = (
            "Plan de campana construido con un flujo multi-herramienta: resultados electorales, abstencion, "
            "poblacion, edad, renta y ranking territorial de oportunidad. Si no hay partido objetivo, la lectura "
            "es neutral y el ranking usa PP solo como referencia tecnica inicial para ordenar oportunidades."
        )
        warnings = list(collected.warnings)
        if plan.target_party is None:
            warnings.append("Para afinar el analisis puedo adaptar la estrategia a un partido, presupuesto o candidato concreto.")
        return self._output("campaign_plan_workflow", rows, collected, methodology, warnings, plan)

    def _candidate_visit_plan(self, plan: PoliticalPlan, year: int) -> WorkflowOutput:
        party = plan.target_party or "PP"
        collected = self._collect(
            [
                ("rank_sections_by_opportunity", lambda: self.tools.rank_sections_by_opportunity(plan.municipality_id, target_party=party, year=year, limit=10)),
                ("build_campaign_recommendation", lambda: self.tools.build_campaign_recommendation(plan.municipality_id, target_party=party, year=year)),
            ]
        )
        rows = _merge_evidence(collected.results, mode="candidate_visit_plan", target_party=plan.target_party)
        return self._output(
            "candidate_visit_plan_workflow",
            rows,
            collected,
            "Plan de visitas construido priorizando oportunidad electoral, abstencion, competitividad y tamano territorial.",
            collected.warnings,
            plan,
        )

    def _abstention_analysis(self, plan: PoliticalPlan, year: int) -> WorkflowOutput:
        party = plan.target_party or "PP"
        collected = self._collect(
            [
                ("get_turnout_analysis", lambda: self.tools.get_turnout_analysis(plan.municipality_id, year=year, limit=12)),
                ("rank_sections_by_opportunity", lambda: self.tools.rank_sections_by_opportunity(plan.municipality_id, target_party=party, year=year, limit=12)),
            ]
        )
        rows = _merge_evidence(collected.results, mode="abstention_analysis", target_party=plan.target_party)
        rows.sort(key=lambda row: _number(row.get("abstention_rate_pct")) or -1, reverse=True)
        return self._output(
            "abstention_analysis_workflow",
            rows,
            collected,
            "Analisis de abstencion por seccion: censo menos votos emitidos sobre censo, enriquecido con ranking territorial.",
            collected.warnings,
            plan,
        )

    def _party_growth_opportunity(self, plan: PoliticalPlan, year: int) -> WorkflowOutput:
        party = plan.target_party or "PP"
        collected = self._collect(
            [
                ("get_election_results", lambda: self.tools.get_election_results(plan.municipality_id, party=party, year=year, limit=12)),
                ("rank_sections_by_opportunity", lambda: self.tools.rank_sections_by_opportunity(plan.municipality_id, target_party=party, year=year, limit=10)),
                ("build_campaign_recommendation", lambda: self.tools.build_campaign_recommendation(plan.municipality_id, target_party=party, year=year)),
            ]
        )
        rows = _merge_evidence(collected.results, mode="party_growth_opportunity", target_party=party)
        return self._output(
            "party_growth_opportunity_workflow",
            rows,
            collected,
            f"Oportunidad de crecimiento para {party}: combina voto observado, distancia al ganador, abstencion y tamano seccional.",
            collected.warnings,
            plan,
        )

    def _territorial_marketing(self, plan: PoliticalPlan, year: int) -> WorkflowOutput:
        collected = self._collect(
            [
                ("get_age_structure", lambda: self.tools.get_age_structure(plan.municipality_id, limit=12, youngest=True)),
                ("get_family_youth_profile", lambda: self.tools.get_family_youth_profile(plan.municipality_id, year=year, limit=12)),
                ("get_population_trend", lambda: self.tools.get_population_trend(plan.municipality_id, year=year, limit=12)),
                ("get_population_density", lambda: self.tools.get_population_density(plan.municipality_id, year=year, limit=12)),
                ("get_income_profile", lambda: self.tools.get_income_profile(plan.municipality_id, year=year, limit=12)),
                ("get_socioeconomic_profile", lambda: self.tools.get_socioeconomic_profile(plan.municipality_id, year=year, limit=12)),
                ("get_land_built_profile", lambda: self.tools.get_land_built_profile(plan.municipality_id, year=year, limit=12)),
                ("get_foreign_population_profile", lambda: self.tools.get_foreign_population_profile(plan.municipality_id, year=year, limit=12)),
            ]
        )
        rows = _merge_territorial_evidence(collected.results, plan)
        methodology = (
            "Ranking territorial no electoral: combina estructura de edad, crecimiento residencial, densidad/poblacion, "
            "renta y entorno urbano cuando estan disponibles. No usa voto, partidos ni resultados electorales."
        )
        warnings = list(collected.warnings)
        if plan.target_service:
            methodology += f" Servicio objetivo: {plan.target_service}."
        return self._output(f"{plan.goal}_workflow", rows, collected, methodology, warnings, plan)

    def _sports_facilities_planning(self, plan: PoliticalPlan, year: int) -> WorkflowOutput:
        output = self._territorial_marketing(plan, year)
        output.tool_result.name = "sports_facilities_planning_workflow"
        output.tool_result.methodology = (
            "Priorizacion de instalaciones deportivas: combina poblacion joven, tamano poblacional, densidad, "
            "crecimiento residencial, presion urbana y senales socioeconomicas. No usa votos ni plantillas comerciales."
        )
        return output

    def _real_estate_location_advice(self, plan: PoliticalPlan, year: int) -> WorkflowOutput:
        output = self._territorial_marketing(plan, year)
        output.tool_result.name = "real_estate_location_advice_workflow"
        output.tool_result.methodology = (
            "Recomendacion residencial: compara zonas con crecimiento, densidad, renta y entorno urbano para orientar "
            "compra de vivienda. No usa partidos, campana ni promocion de servicios."
        )
        return output

    def _labor_training_outreach(self, plan: PoliticalPlan, year: int) -> WorkflowOutput:
        collected = self._collect(
            [
                ("rank_sections_for_labor_training_outreach", lambda: self.tools.rank_sections_for_labor_training_outreach(plan.municipality_id, year=year, limit=12)),
                ("get_socioeconomic_intelligence_profile", lambda: self.tools.get_socioeconomic_intelligence_profile(plan.municipality_id, year=year, limit=12)),
                ("get_population_density", lambda: self.tools.get_population_density(plan.municipality_id, year=year, limit=12)),
                ("get_income_profile", lambda: self.tools.get_income_profile(plan.municipality_id, year=year, limit=12)),
            ]
        )
        rows = _merge_territorial_evidence(collected.results, plan)
        return self._output(
            "labor_training_outreach_workflow",
            rows,
            collected,
            "Flujo de formacion laboral: usa Inteligencia Socioeconomica, poblacion, densidad y renta para priorizar secciones.",
            collected.warnings,
            plan,
        )

    def _public_service_outreach(self, plan: PoliticalPlan, year: int) -> WorkflowOutput:
        collected = self._collect(
            [
                ("get_socioeconomic_intelligence_profile", lambda: self.tools.get_socioeconomic_intelligence_profile(plan.municipality_id, year=year, limit=12)),
                ("get_population_density", lambda: self.tools.get_population_density(plan.municipality_id, year=year, limit=12)),
                ("get_income_profile", lambda: self.tools.get_income_profile(plan.municipality_id, year=year, limit=12)),
            ]
        )
        rows = _merge_territorial_evidence(collected.results, plan)
        return self._output(
            "public_service_outreach_workflow",
            rows,
            collected,
            "Flujo de comunicacion publica: usa Inteligencia Socioeconomica, poblacion, densidad y renta para priorizar alcance territorial.",
            collected.warnings,
            plan,
        )

    def _general_territorial_advice(self, plan: PoliticalPlan, year: int) -> WorkflowOutput:
        output = self._territorial_marketing(plan, year)
        output.tool_result.name = f"{plan.goal}_workflow"
        output.tool_result.methodology = (
            "Consejo territorial general: cruza edad, poblacion, crecimiento, renta, densidad y entorno urbano para "
            "priorizar zonas sin forzar un marco electoral o comercial."
        )
        return output

    def _output(
        self,
        name: str,
        rows: list[dict[str, Any]],
        collected: "_CollectedResults",
        methodology: str,
        warnings: list[str],
        plan: PoliticalPlan,
    ) -> WorkflowOutput:
        data_used = sorted({source for result in collected.results for source in result.data_used})
        return WorkflowOutput(
            tool_result=AnalystToolResult(
                name=name,
                rows=rows,
                data_used=data_used,
                methodology=methodology,
                warnings=_user_friendly_warnings(warnings),
            ),
            tool_names=collected.tool_names,
            plan=plan,
        )

    def _collect(self, calls: list[tuple[str, Callable[[], AnalystToolResult]]]) -> "_CollectedResults":
        results: list[AnalystToolResult] = []
        tool_names: list[str] = []
        warnings: list[str] = []
        for name, call in calls:
            try:
                result = call()
                results.append(result)
                tool_names.append(result.name)
                warnings.extend(result.warnings)
            except Exception:
                warnings.append("No se pudo incorporar una fuente interna complementaria para este analisis.")
        return _CollectedResults(results=results, tool_names=tool_names, warnings=warnings)


@dataclass(slots=True)
class _CollectedResults:
    results: list[AnalystToolResult]
    tool_names: list[str]
    warnings: list[str]


def _merge_evidence(results: list[AnalystToolResult], *, mode: str, target_party: str | None) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for result in results:
        for raw in result.rows:
            section_id = str(raw.get("section_id") or "")
            if not section_id:
                continue
            row = merged.setdefault(section_id, {field: None for field in EVIDENCE_FIELDS})
            row["section_id"] = section_id
            row["section_name"] = raw.get("section_name") or raw.get("name") or row.get("section_name") or section_id
            _copy(row, raw, "population_total", "population_total")
            _copy(row, raw, "winning_party", "winning_party")
            _copy(row, raw, "winning_party_pct", "winning_party_pct")
            _copy(row, raw, "runner_up_pct", "runner_up_pct")
            _copy(row, raw, "victory_margin_pct", "victory_margin_pct")
            _copy(row, raw, "target_party_vote_pct", "target_party_vote_pct")
            _copy(row, raw, "abstention_rate_pct", "abstention_rate_pct")
            _copy(row, raw, "population_growth_pct", "population_growth_pct")
            _copy(row, raw, "average_age", "avg_age")
            _copy(row, raw, "individual_income", "income")
            _copy(row, raw, "opportunity_score", "opportunity_score")
            if row.get("target_party_vote_pct") is None and raw.get("vote_pct") is not None:
                row["target_party_vote_pct"] = raw.get("vote_pct")
    rows = list(merged.values())
    for row in rows:
        row["strategic_label"] = _strategic_label(row, mode)
        row["reason"] = _reason(row, mode, target_party)
    rows.sort(
        key=lambda row: (
            _number(row.get("opportunity_score")) or 0,
            _number(row.get("abstention_rate_pct")) or 0,
            _number(row.get("population_total")) or 0,
        ),
        reverse=True,
    )
    return rows[:12]


def _merge_territorial_evidence(results: list[AnalystToolResult], plan: PoliticalPlan) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for result in results:
        for raw in result.rows:
            section_id = str(raw.get("section_id") or "")
            if not section_id:
                continue
            row = merged.setdefault(section_id, {field: None for field in EVIDENCE_FIELDS})
            row["section_id"] = section_id
            row["section_name"] = raw.get("section_name") or row.get("section_name") or section_id
            _copy(row, raw, "population_total", "population_total")
            _copy(row, raw, "population_density", "population_density")
            _copy(row, raw, "population_growth_pct", "population_growth_pct")
            _copy(row, raw, "average_age", "avg_age")
            _copy(row, raw, "under_30_pct", "under_30_pct")
            _copy(row, raw, "over_65_pct", "over_65_pct")
            _copy(row, raw, "individual_income", "income")
            _copy(row, raw, "urban_intensity_index", "urban_intensity_index")
            _copy(row, raw, "parcel_density", "parcel_density")
            _copy(row, raw, "labor_training_score", "labor_training_score")
            _copy(row, raw, "productive_complexity_index", "productive_complexity_index")
            _copy(row, raw, "productive_complexity_label", "productive_complexity_label")
            _copy(row, raw, "vulnerability_index", "vulnerability_index")
            _copy(row, raw, "human_capital_index", "human_capital_index")
            _copy(row, raw, "resilience_index", "resilience_index")
            _copy(row, raw, "employment_norm", "employment_norm")
            _copy(row, raw, "unemployment_norm", "unemployment_norm")
            _copy(row, raw, "qualified_occupation_norm", "qualified_occupation_norm")
            _copy(row, raw, "low_education_norm", "low_education_norm")
            _copy(row, raw, "pct_employed", "pct_employed")
            _copy(row, raw, "pct_unemployed", "pct_unemployed")
            _copy(row, raw, "pct_qualified_occupations", "pct_qualified_occupations")
    rows = list(merged.values())
    for row in rows:
        score = _territorial_score(row, plan)
        row["opportunity_score"] = round(score, 2)
        row["score"] = round(score, 2)
        row["strategic_label"] = _territorial_label(row, plan)
        row["target_audience_reason"] = _territorial_reason(row, plan)
        row["recommended_channel"] = _territorial_channel(row, plan)
        row["recommended_action"] = _territorial_action(row, plan)
        row["data_support"] = _territorial_support(row)
        row["reason"] = row["target_audience_reason"]
    rows.sort(key=lambda item: _number(item.get("score")) or 0, reverse=True)
    for index, row in enumerate(rows, start=1):
        row["priority"] = index
    return rows[:10]


def _territorial_score(row: dict[str, Any], plan: PoliticalPlan) -> float:
    if plan.goal == "labor_training_outreach" and _number(row.get("labor_training_score")) is not None:
        return _number(row.get("labor_training_score")) or 0
    if plan.goal == "public_service_outreach":
        vulnerability = _number(row.get("vulnerability_index")) or 0
        unemployment = _number(row.get("unemployment_norm")) or 0
        population = _number(row.get("population_total")) or 0
        density = _number(row.get("population_density")) or 0
        return min(vulnerability * 0.42 + unemployment * 0.28 + min(population / 40, 20) + min(density / 350, 10), 100)
    under_30 = _number(row.get("under_30_pct")) or 0
    growth = max(_number(row.get("population_growth_pct")) or 0, 0)
    population = _number(row.get("population_total")) or 0
    density = _number(row.get("population_density")) or 0
    income = _number(row.get("income"))
    urban = _number(row.get("urban_intensity_index")) or 0
    score = 0.0
    score += min(under_30, 45) * 1.0
    score += min(growth * 4, 25)
    score += min(population / 120, 20)
    score += min(density / 150, 15)
    score += min(urban * 5, 10)
    if plan.goal == "sports_facilities_planning":
        score += min(density / 120, 18)
        score += min(under_30, 40) * 0.6
        if income is not None and income < 15500:
            score += 8
    if plan.goal == "real_estate_location_advice":
        score += min(max(growth, 0) * 3, 18)
        score += min(urban * 6, 12)
        if income is not None:
            score += 10 if income >= 14500 else 4
    if income is not None:
        if plan.target_service and "free" in plan.target_service.lower():
            score += 12 if 11000 <= income <= 17000 else 5
        else:
            score += 10 if income >= 14000 else 5
    return score


def _territorial_label(row: dict[str, Any], plan: PoliticalPlan) -> str:
    if plan.goal == "labor_training_outreach":
        if (_number(row.get("productive_complexity_index")) or 0) >= 60:
            return "alto potencial productivo"
        if (_number(row.get("vulnerability_index")) or 0) >= 60:
            return "necesidad de recualificacion"
        return "oportunidad de formacion laboral"
    if plan.goal == "sports_facilities_planning":
        if (_number(row.get("under_30_pct")) or 0) >= 30 and (_number(row.get("population_density")) or 0) > 1500:
            return "prioridad deportiva juvenil y densa"
        if (_number(row.get("population_growth_pct")) or 0) >= 3:
            return "demanda deportiva por crecimiento residencial"
        return "necesidad deportiva de proximidad"
    if plan.goal == "real_estate_location_advice":
        if (_number(row.get("population_growth_pct")) or 0) >= 3 and (_number(row.get("urban_intensity_index")) or 0) > 1:
            return "zona residencial en consolidacion"
        if (_number(row.get("income")) or 0) >= 14500:
            return "perfil residencial solvente"
        return "opcion residencial a evaluar"
    if plan.goal == "public_service_outreach":
        if (_number(row.get("vulnerability_index")) or 0) >= 60:
            return "prioridad de comunicacion por vulnerabilidad"
        if (_number(row.get("unemployment_norm")) or 0) >= 60:
            return "prioridad por senal de desempleo"
        return "prioridad de comunicacion publica"
    if (_number(row.get("under_30_pct")) or 0) >= 30:
        return "familias y poblacion joven"
    if (_number(row.get("population_growth_pct")) or 0) >= 3:
        return "crecimiento residencial"
    if (_number(row.get("population_density")) or 0) > 1500:
        return "alta densidad urbana"
    return "oportunidad territorial"


def _territorial_reason(row: dict[str, Any], plan: PoliticalPlan) -> str:
    parts: list[str] = []
    if row.get("under_30_pct") is not None:
        parts.append(f"poblacion joven {_fmt(row.get('under_30_pct'))}%")
    if row.get("population_growth_pct") is not None:
        parts.append(f"crecimiento residencial {_fmt(row.get('population_growth_pct'))}%")
    if row.get("population_total") is not None:
        parts.append(f"tamano poblacional {row.get('population_total')}")
    if row.get("income") is not None:
        parts.append(f"renta media {_fmt(row.get('income'))} EUR")
    if row.get("population_density") is not None:
        parts.append(f"densidad {_fmt(row.get('population_density'))}")
    if plan.goal == "labor_training_outreach":
        labor_parts: list[str] = []
        if row.get("productive_complexity_index") is not None:
            labor_parts.append(f"potencial productivo {_fmt(row.get('productive_complexity_index'))}")
        if row.get("vulnerability_index") is not None:
            labor_parts.append(f"vulnerabilidad socioeconomica {_fmt(row.get('vulnerability_index'))}")
        if row.get("employment_norm") is not None:
            labor_parts.append(f"empleo {_fmt(row.get('employment_norm'))}")
        if row.get("unemployment_norm") is not None:
            labor_parts.append(f"desempleo {_fmt(row.get('unemployment_norm'))}")
        if row.get("low_education_norm") is not None:
            labor_parts.append(f"necesidad formativa proxy {_fmt(row.get('low_education_norm'))}")
        if labor_parts:
            return "Para formacion laboral, prioriza porque combina " + ", ".join(labor_parts[:4]) + "."
        return "Para formacion laboral, prioriza por senales socioeconomicas disponibles."
    if plan.goal == "public_service_outreach":
        public_parts: list[str] = []
        if row.get("vulnerability_index") is not None:
            public_parts.append(f"vulnerabilidad socioeconomica {_fmt(row.get('vulnerability_index'))}")
        if row.get("unemployment_norm") is not None:
            public_parts.append(f"desempleo {_fmt(row.get('unemployment_norm'))}")
        if row.get("low_education_norm") is not None:
            public_parts.append(f"necesidad formativa/social proxy {_fmt(row.get('low_education_norm'))}")
        public_parts.extend(parts[:2])
        if public_parts:
            return "Para comunicación pública, prioriza porque combina " + ", ".join(public_parts[:4]) + "."
        return "Para comunicación pública, prioriza por senales socioeconomicas disponibles."
    if not parts:
        return "Interesa por senales territoriales disponibles, aunque faltan indicadores directos para esta decision."
    if plan.goal == "sports_facilities_planning":
        return "Para instalaciones deportivas, prioriza porque combina " + ", ".join(parts[:4]) + "."
    if plan.goal == "real_estate_location_advice":
        return "Para compra de vivienda, conviene analizarla porque combina " + ", ".join(parts[:4]) + "."
    if plan.goal in {"urban_planning", "socioeconomic_analysis", "general_territorial_advice"}:
        return "Territorialmente destaca porque combina " + ", ".join(parts[:4]) + "."
    service = _service_label(plan.target_service)
    return f"Para {service}, interesa porque combina " + ", ".join(parts[:4]) + "."


def _territorial_channel(row: dict[str, Any], plan: PoliticalPlan) -> str:
    label = _territorial_label(row, plan)
    if plan.goal == "sports_facilities_planning":
        if "juvenil" in label:
            return "centros educativos, clubes deportivos, asociaciones vecinales y observacion de uso de espacios"
        if "crecimiento" in label:
            return "participacion vecinal, inspeccion urbana y coordinacion con servicios municipales"
        return "diagnostico de demanda, asociaciones locales y mapa de accesibilidad peatonal"
    if plan.goal == "real_estate_location_advice":
        if "consolidacion" in label:
            return "visita de zona, comparativa de servicios, movilidad y tension residencial"
        if "solvente" in label:
            return "comparativa de precios, renta del entorno, servicios y calidad urbana"
        return "analisis de vivienda concreta, accesibilidad, ruido, servicios y trayectoria de la zona"
    if plan.goal == "public_service_outreach":
        return "servicios sociales, centros municipales, asociaciones vecinales, oficinas de empleo y carteleria en equipamientos publicos"
    if plan.goal == "labor_training_outreach":
        return "servicios de empleo y orientacion, centros municipales, asociaciones vecinales, comercios de proximidad y campanas geolocalizadas sobrias"
    if plan.goal in {"urban_planning", "socioeconomic_analysis", "general_territorial_advice"}:
        return "validacion en campo, contraste con servicios cercanos y revision de indicadores territoriales"
    if "joven" in label:
        return "colegios, AMPAs, Instagram/TikTok geolocalizado y grupos vecinales"
    if "crecimiento" in label:
        return "buzoneo selectivo, comercios de proximidad, carteleria local y anuncios geolocalizados"
    if "densidad" in label:
        return "puntos de paso, comercios, carteleria y prueba gratuita con reserva por WhatsApp"
    return "comercios locales, asociaciones vecinales y publicidad digital de radio corto"


def _territorial_action(row: dict[str, Any], plan: PoliticalPlan) -> str:
    service = _service_label(plan.target_service) or "servicio"
    if plan.goal == "public_service_outreach":
        return "concentrar comunicacion publica con servicios sociales, centros municipales, asociaciones vecinales, oficinas de empleo y carteleria clara."
    if plan.goal == "labor_training_outreach":
        return "intensificar difusion de la formacion con servicios de empleo, centros municipales, asociaciones vecinales y colaboracion con empresas locales."
    if plan.goal == "sports_facilities_planning":
        return "priorizar estudio de pista multideporte o equipamiento deportivo de proximidad, validando demanda y suelo disponible."
    if plan.goal == "real_estate_location_advice":
        return "comparar vivienda concreta con servicios, movilidad, densidad, renta del entorno y posible revalorizacion antes de decidir."
    if plan.goal in {"urban_planning", "socioeconomic_analysis", "general_territorial_advice"}:
        return "hacer una validacion territorial corta, comparar indicadores y decidir con criterios operativos antes de invertir recursos."
    return f"promocionar el {service} con una oferta simple, formulario WhatsApp, prueba gratuita y colaboraciones locales."


def _territorial_support(row: dict[str, Any]) -> list[str]:
    support: list[str] = []
    for label, key in [
        ("poblacion", "population_total"),
        ("jovenes", "under_30_pct"),
        ("crecimiento", "population_growth_pct"),
        ("renta", "income"),
        ("densidad", "population_density"),
        ("potencial_productivo", "productive_complexity_index"),
        ("vulnerabilidad", "vulnerability_index"),
        ("empleo", "employment_norm"),
        ("desempleo", "unemployment_norm"),
    ]:
        if row.get(key) is not None:
            support.append(f"{label}: {row.get(key)}")
    return support


def _service_label(service: str | None) -> str:
    if service == "free English course":
        return "curso gratuito de inglés"
    if service == "English course":
        return "curso de inglés"
    return service or "servicio"


def _copy(target: dict[str, Any], source: dict[str, Any], source_key: str, target_key: str) -> None:
    value = source.get(source_key)
    if value is not None:
        target[target_key] = value


def _strategic_label(row: dict[str, Any], mode: str) -> str:
    abstention = _number(row.get("abstention_rate_pct")) or 0
    margin = _number(row.get("victory_margin_pct")) or 99
    target_pct = _number(row.get("target_party_vote_pct"))
    winning_pct = _number(row.get("winning_party_pct"))
    if mode == "abstention_analysis" or abstention >= 45:
        return "movilizacion"
    if margin <= 7:
        return "persuasion"
    if target_pct is not None and winning_pct is not None and target_pct >= winning_pct - 3:
        return "retencion"
    if mode == "candidate_visit_plan":
        return "visita prioritaria"
    return "expansion"


def _reason(row: dict[str, Any], mode: str, target_party: str | None) -> str:
    parts: list[str] = []
    if row.get("opportunity_score") is not None:
        parts.append(f"score de oportunidad {_fmt(row.get('opportunity_score'))}")
    if row.get("abstention_rate_pct") is not None:
        parts.append(f"abstencion {_fmt(row.get('abstention_rate_pct'))}%")
    if row.get("victory_margin_pct") is not None:
        parts.append(f"margen {_fmt(row.get('victory_margin_pct'))} puntos")
    if row.get("population_total") is not None:
        parts.append(f"poblacion {row.get('population_total')}")
    if target_party and row.get("target_party_vote_pct") is not None:
        parts.append(f"{target_party} {_fmt(row.get('target_party_vote_pct'))}%")
    if not parts:
        return "Se incluye por disponibilidad de evidencia seccional en el flujo aprobado."
    prefix = {
        "candidate_visit_plan": "Importa para visita porque combina presencia territorial y valor politico",
        "abstention_analysis": "Importa para movilizacion porque concentra abstencion observable",
        "party_growth_opportunity": "Importa para crecimiento porque combina voto observado y oportunidad",
    }.get(mode, "Importa estrategicamente porque combina varias senales territoriales")
    return f"{prefix}: " + ", ".join(parts) + "."


def _user_friendly_warnings(warnings: list[str]) -> list[str]:
    output: list[str] = []
    for warning in warnings:
        if not warning:
            continue
        if "No se pudo incorporar" in warning:
            output.append(warning)
        elif "Para afinar" in warning:
            output.append(warning)
        elif "No section" in warning:
            output.append("No se encontro informacion para alguna seccion solicitada.")
        elif "fallback" not in warning.lower() and "debug" not in warning.lower():
            output.append(warning)
    return list(dict.fromkeys(output))


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value: Any) -> str:
    number = _number(value)
    return "" if number is None else f"{number:.1f}"


def _plan_years(plan: PoliticalPlan, *, fallback_end_year: int) -> tuple[int, int]:
    if plan.start_year and plan.end_year:
        return plan.start_year, plan.end_year
    text = " ".join(
        item
        for item in [plan.clarification_question or "", plan.goal]
        if item
    )
    years = [int(value) for value in re.findall(r"20\d{2}", text)]
    if len(years) >= 2:
        return years[0], years[1]
    return fallback_end_year - 4, fallback_end_year
