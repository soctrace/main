from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class GuardResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    repair_hint: str | None = None
    route_to_followup: bool = False


class IntentGuard:
    def validate_tool_choice(
        self,
        question: str,
        tool_name: str,
        arguments: dict[str, Any],
        semantic_interpretation: dict | None = None,
    ) -> GuardResult:
        text = _normalize(question)
        reasons: list[str] = []

        if _is_followup_metadata_question(text):
            return GuardResult(
                ok=False,
                reasons=["follow-up metadata question must be answered from memory"],
                repair_hint="No llames a ninguna herramienta. Resuelve la pregunta desde FollowUpResolver y la memoria persistente.",
                route_to_followup=True,
            )

        if _is_age_cohort_question(text):
            if tool_name not in {"age_cohort_projection", "aggregate_municipality"}:
                return GuardResult(
                    ok=False,
                    reasons=[f"age cohort question cannot use `{tool_name}`"],
                    repair_hint=_age_repair_hint(text),
                )

        if _is_participation_or_abstention_question(text):
            metric = arguments.get("metric")
            expected_metric = "abstention_pct" if "abstencion" in text else "participation_pct"
            if tool_name != "rank_sections":
                reasons.append("participation/abstention questions must use rank_sections")
            if metric != expected_metric:
                reasons.append(f"expected metric `{expected_metric}`, got `{metric}`")
            if reasons:
                return GuardResult(
                    ok=False,
                    reasons=reasons,
                    repair_hint=(
                        f"La pregunta pide {'abstencion' if expected_metric == 'abstention_pct' else 'participacion'} por sección. "
                        f"Usa rank_sections con metric={expected_metric}, order={_participation_order(text)}, "
                        "election_type=MUNICIPALES y sin year si el usuario no especifica elección."
                    ),
                )

        if _is_age_group_voting_question(text) and tool_name != "ecological_vote_profile_by_age_group":
            return GuardResult(
                ok=False,
                reasons=["age-group voting question must use ecological_vote_profile_by_age_group"],
                repair_hint=(
                    "La pregunta pide inferir qué vota un grupo de edad. Usa ecological_vote_profile_by_age_group "
                    "con el rango de edad solicitado. No uses rank_sections ni métricas demográficas como respuesta final."
                ),
            )

        return GuardResult(ok=True)


def _normalize(value: str) -> str:
    value = value.lower()
    value = "".join(ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn")
    return value


def _is_age_cohort_question(text: str) -> bool:
    return bool(
        re.search(
            r"personas tendran 18|18 anos en 2027|votar por primera vez|personas tenian entre 18 y 22|entre 18 y 22|cohorte|rango de edad",
            text,
        )
    )


def _is_participation_or_abstention_question(text: str) -> bool:
    return bool(
        re.search(
            r"menor abstencion|mayor abstencion|mayor participacion|menor participacion|donde vota mas|donde vota menos",
            text,
        )
    )


def _is_followup_metadata_question(text: str) -> bool:
    return bool(re.search(r"en que ano|que ano|de que ano|mas poblada en que ano|ese dato de que ano|son datos de", text))


def _is_age_group_voting_question(text: str) -> bool:
    return bool(
        re.search(
            r"que suelen votar|que votan|voto de los jovenes|voto de los mayores|mayores de 45|menores de 30",
            text,
        )
    )


def _participation_order(text: str) -> str:
    return "asc" if re.search(r"menor|menos", text) else "desc"


def _age_repair_hint(text: str) -> str:
    if re.search(r"18 anos en 2027|personas tendran 18", text):
        return (
            "La pregunta pide calcular personas que tendrán 18 años en 2027. "
            "Usa age_cohort_projection con source_year=2025, source_age=16, target_year=2027, "
            "target_age=18, group_by=municipality_and_section. No uses rank_sections ni participation_pct."
        )
    if re.search(r"entre 18 y 22", text):
        return (
            "La pregunta pide una cohorte de edad 18-22 en 2023. Usa age_cohort_projection con "
            "min_age=18, max_age=22, source_year=2023, group_by=municipality_and_section. "
            "No uses participation_pct ni rank_sections."
        )
    return "La pregunta pide una cohorte de edad. Usa age_cohort_projection o aggregate_municipality."
