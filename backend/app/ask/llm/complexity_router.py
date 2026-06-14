from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from pydantic import BaseModel, Field

from app.ask.llm.schemas import LLMComplexityLevel


logger = logging.getLogger(__name__)


class ComplexityRouterInput(BaseModel):
    question: str
    locale: str = "es-ES"
    semantic_interpretation: dict[str, Any] | None = None
    conversation_context: dict[str, Any] = Field(default_factory=dict)
    active_municipality: str | None = "29070"
    active_year: int | None = None


class ComplexityRouterResult(BaseModel):
    complexity: LLMComplexityLevel
    score: int
    reasons: list[str] = Field(default_factory=list)
    recommended_provider_notes: dict[str, Any] = Field(default_factory=dict)


SIMPLE_OPERATIONS = {
    "rank_sections",
    "aggregate_municipality",
    "section_profile",
    "persistent_winner",
    "party_strength",
    "historical_party_average",
}

SEMI_COMPLEX_OPERATIONS = {
    "compare_years",
    "population_growth",
    "age_cohort_projection",
    "filter_sections",
}

COMPLEX_OPERATIONS = {
    "correlation_analysis",
    "correlation",
    "clustering",
    "prediction",
    "scenario_analysis",
}


class ComplexityRouter:
    def classify(self, router_input: ComplexityRouterInput | dict[str, Any] | str) -> ComplexityRouterResult:
        if isinstance(router_input, str):
            payload = ComplexityRouterInput(question=router_input)
        elif isinstance(router_input, dict):
            payload = ComplexityRouterInput(**router_input)
        else:
            payload = router_input

        question = _normalize(payload.question)
        score = 0
        reasons: list[str] = []
        semantic_result = self._classify_semantic(payload.semantic_interpretation)
        if semantic_result:
            score += semantic_result.score
            reasons.extend(semantic_result.reasons)

        semi_signal = False
        complex_signal = False

        if self._is_metadata_followup(question):
            score -= 1
            reasons.append("metadata follow-up")

        semi_points, semi_reasons = self._semi_complex_score(question)
        if semi_points:
            semi_signal = True
            score += semi_points
            reasons.extend(semi_reasons)

        complex_points, complex_reasons = self._complex_score(question)
        if complex_points:
            complex_signal = True
            score += complex_points
            reasons.extend(complex_reasons)

        domain_points, domain_reasons = self._domain_score(question)
        if domain_points:
            score += domain_points
            reasons.extend(domain_reasons)

        score = max(0, score)
        complexity = self._level_for_score(score)

        if semantic_result and semantic_result.complexity in {"simple", "semi_complex"} and not complex_signal:
            complexity = semantic_result.complexity
        if semi_signal and complexity == "simple":
            complexity = "semi_complex"
            score = max(score, 3)
        if complex_signal:
            complexity = "complex"
            score = max(score, 6)

        result = ComplexityRouterResult(
            complexity=complexity,
            score=score,
            reasons=_dedupe(reasons) or ["direct lookup"],
            recommended_provider_notes={
                "provider_agnostic": True,
                "model_selection": "provider",
            },
        )
        logger.debug(
            "Complexity routing decision",
            extra={
                "question": payload.question,
                "complexity": result.complexity,
                "complexity_score": result.score,
                "complexity_reasons": result.reasons,
            },
        )
        return result

    def _classify_semantic(self, semantic_interpretation: dict[str, Any] | None) -> ComplexityRouterResult | None:
        if not semantic_interpretation:
            return None
        confidence = str(semantic_interpretation.get("confidence") or "medium").lower()
        if confidence == "low":
            return None

        operation = str(semantic_interpretation.get("operation") or "").strip()
        metrics = semantic_interpretation.get("metrics") or []
        if operation in SIMPLE_OPERATIONS:
            return ComplexityRouterResult(complexity="simple", score=0, reasons=[f"semantic operation: {operation}"])
        if operation in SEMI_COMPLEX_OPERATIONS:
            return ComplexityRouterResult(complexity="semi_complex", score=3, reasons=[f"semantic operation: {operation}"])
        if operation == "cross_metric_ranking":
            metric_count = len(metrics) if isinstance(metrics, list) else 0
            if metric_count > 2:
                return ComplexityRouterResult(complexity="complex", score=6, reasons=["semantic operation: cross_metric_ranking with multiple metrics"])
            return ComplexityRouterResult(complexity="semi_complex", score=4, reasons=["semantic operation: cross_metric_ranking"])
        if operation in COMPLEX_OPERATIONS:
            return ComplexityRouterResult(complexity="complex", score=6, reasons=[f"semantic operation: {operation}"])
        return None

    def _semi_complex_score(self, question: str) -> tuple[int, list[str]]:
        checks: list[tuple[str, str]] = [
            (r"\bdesde\b", "temporal expression"),
            (r"\bentre\s+\d{4}\s+y\s+\d{4}\b", "year range comparison"),
            (r"\bevoluci[oó]n\b|\bevolucionado\b|\bevolucion\b", "historical evolution"),
            (r"\bha crecido\b|\bhan crecido\b|\bcrecido mas\b|\bcrecimiento\b", "growth analysis"),
            (r"\bha rejuvenecido\b|\brejuvenecimiento\b", "age temporal comparison"),
            (r"\btendra(?:n)?\s+18\b|\btendran\s+18\b", "age cohort projection"),
            (r"\bpodran votar por primera vez\b", "first-time voter projection"),
            (r"\bd['’]?hondt\b|\bdhondt\b", "D'Hondt calculation"),
            (r"\bpor seccion\b.*\b(edad|voto|abstencion)\b|\b(edad|voto|abstencion)\b.*\bpor seccion\b", "section-level age/electoral analysis"),
            (r"\bde\s+\d+\s+a\s+\d+\s+anos\b.*\b(abstuvieron|votaron|voto|abstencion)\b", "age cohort electoral analysis"),
            (r"\bsuperan\s+(?:los\s+)?[\d.,]+|\bpor encima de\b|\bpor debajo de\b", "threshold filter"),
            (r"\bcombinan\b|\bcombina\b", "combined indicators"),
        ]
        reasons = [reason for pattern, reason in checks if re.search(pattern, question)]
        if not reasons:
            return 0, []
        score = 2 * len(reasons)
        if any(reason in reasons for reason in ("age cohort projection", "threshold filter", "D'Hondt calculation", "combined indicators", "growth analysis")):
            score += 1
        return score, reasons

    def _complex_score(self, question: str) -> tuple[int, list[str]]:
        checks: list[tuple[str, str]] = [
            (r"\bestrategia\b", "strategic advice"),
            (r"\brecomienda\b|\brecomendar\b|\bdeberia\b|\bdeberian\b", "recommendation request"),
            (r"\bdiagnostico\b", "open-ended diagnosis"),
            (r"\brelacion entre\b|\bse relacionan\b|\brelacion existe\b", "relationship analysis"),
            (r"\bcorrelaci[oó]n\b|\bcorrelacion\b", "correlation analysis"),
            (r"\bagrupa\b|\bagrupar\b|\bcluster\b|\bclustering\b", "clustering request"),
            (r"\bpredice\b|\bpredecir\b|\bpredicci[oó]n\b|\bpodrian cambiar\b", "prediction request"),
            (r"\bindice\b", "index construction"),
            (r"\boportunidad\b", "opportunity analysis"),
            (r"\bvulnerabilidad\b", "vulnerability analysis"),
            (r"\bpor que\b|\bporque\b", "causal explanation"),
            (r"\bcausa\b|\bcausal\b", "causal analysis"),
            (r"\bimpacto\b", "impact analysis"),
            (r"\batipic[ao]s?\b|\boutliers?\b", "outlier detection"),
            (r"\bperfiles similares\b|\bdetecta perfiles\b", "profile detection"),
        ]
        reasons = [reason for pattern, reason in checks if re.search(pattern, question)]
        if not reasons:
            return 0, []
        return 4 * len(reasons), reasons

    def _domain_score(self, question: str) -> tuple[int, list[str]]:
        domains = {
            "electoral": [
                "voto",
                "abstencion",
                "participacion",
                "ganador",
                "pp",
                "psoe",
                "vox",
                "municipales",
                "electoral",
            ],
            "demographic": [
                "joven",
                "jovenes",
                "edad",
                "poblacion",
                "habitantes",
                "mayores",
                "jubilados",
            ],
            "income": ["renta", "salario", "pensiones", "pobre", "rica", "ingresos"],
            "housing": ["vivienda", "inmobiliario", "catastral", "residencial", "parcela", "construida"],
        }
        detected = {
            domain
            for domain, keywords in domains.items()
            if any(re.search(rf"\b{re.escape(keyword)}\b", question) for keyword in keywords)
        }

        reasons: list[str] = []
        score = 0
        if {"electoral", "demographic"}.issubset(detected):
            score += 2
            reasons.append("electoral + demographic")
        if {"income", "electoral"}.issubset(detected):
            score += 2
            reasons.append("income + electoral")
        if {"housing", "income"}.issubset(detected):
            score += 2
            reasons.append("housing + income")
        if len(detected) > 2:
            score += 2
            reasons.append("more than two domains")
        return score, reasons

    def _is_metadata_followup(self, question: str) -> bool:
        patterns = [
            r"\bson datos de\s+\d{4}\b",
            r"\bde que ano son\b",
            r"\bcomo lo has calculado\b",
            r"\bcomo se ha calculado\b",
        ]
        return any(re.search(pattern, question) for pattern in patterns)

    def _level_for_score(self, score: int) -> LLMComplexityLevel:
        if score <= 2:
            return "simple"
        if score <= 5:
            return "semi_complex"
        return "complex"


def _normalize(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
