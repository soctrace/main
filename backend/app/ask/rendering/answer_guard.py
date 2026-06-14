from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from app.ask.tools_v2.schemas import ToolResult


FORBIDDEN_CONTENT = re.compile(
    r"\bSELECT\b|\bFROM\s+marts\.|marts\.|core\.|staging\.|raw\.|SQLAlchemy|psycopg|Traceback|\bJSON\b",
    re.IGNORECASE,
)


class RenderGuardResult(BaseModel):
    ok: bool
    reasons: list[str] = Field(default_factory=list)


class RenderAnswerGuard:
    def validate(
        self,
        *,
        question: str,
        answer: str,
        tool_result: ToolResult,
    ) -> RenderGuardResult:
        reasons: list[str] = []
        if FORBIDDEN_CONTENT.search(answer or ""):
            reasons.append("answer exposes forbidden internal content")
        if _asks_age_group_vote(question) and tool_result.tool_name == "rank_sections":
            reasons.append("age-group voting question answered with demographic section ranking")
        if tool_result.tool_name == "ecological_vote_profile_by_age_group":
            lowered = (answer or "").lower()
            if "estimación territorial" not in lowered and "estimacion territorial" not in lowered:
                reasons.append("ecological age-vote answer omits territorial-estimation caveat")
            if "voto individual" not in lowered or "edad" not in lowered:
                reasons.append("ecological age-vote answer omits individual-vote caveat")
        rows = tool_result.rows or []
        if rows:
            first = rows[0]
            self._validate_first_row(answer, first, tool_result, reasons)
            self._validate_entity_list(answer, rows, tool_result, reasons)
        return RenderGuardResult(ok=not reasons, reasons=reasons)

    def _validate_first_row(
        self,
        answer: str,
        first: dict[str, Any],
        tool_result: ToolResult,
        reasons: list[str],
    ) -> None:
        lowered = answer.lower()
        section = first.get("section_name") or first.get("name")
        if section and self._requires_top_entity(tool_result) and section.lower() not in lowered:
            reasons.append("answer omits top section")
        value = first.get("value")
        if value is not None and self._contains_other_number_without_expected(answer, value):
            reasons.append("answer may contradict top value")
        year = first.get("year") or first.get("end_year") or first.get("target_year") or tool_result.metadata.get("year")
        if year is not None and self._requires_year(tool_result) and str(year) not in answer:
            reasons.append("answer omits required year")
        party = first.get("party") or tool_result.metadata.get("party")
        if party and str(party).lower() not in lowered:
            reasons.append("answer omits party")

    def _validate_entity_list(
        self,
        answer: str,
        rows: list[dict[str, Any]],
        tool_result: ToolResult,
        reasons: list[str],
    ) -> None:
        names = [str(row.get("section_name")) for row in rows if row.get("section_name")]
        if 1 < len(names) <= 20 and self._is_entity_list(tool_result):
            missing = [name for name in names if name.lower() not in answer.lower()]
            if missing:
                reasons.append("answer omits entity list items")

    def _requires_top_entity(self, tool_result: ToolResult) -> bool:
        return tool_result.status == "ok" and tool_result.tool_name in {
            "rank_sections",
            "filter_sections",
            "party_strength",
            "historical_party_average",
            "cross_metric_ranking",
            "age_cohort_projection",
            "compare_years",
            "population_growth",
            "section_profile",
        }

    def _requires_year(self, tool_result: ToolResult) -> bool:
        return tool_result.tool_name in {
            "rank_sections",
            "aggregate_municipality",
            "compare_years",
            "population_growth",
            "age_cohort_projection",
        }

    def _is_entity_list(self, tool_result: ToolResult) -> bool:
        return tool_result.tool_name in {
            "persistent_winner",
            "filter_sections",
        }

    def _contains_other_number_without_expected(self, answer: str, expected: Any) -> bool:
        expected_digits = _number_digits(expected)
        if not expected_digits:
            return False
        answer_digits = _normalize_digits(answer)
        if expected_digits in answer_digits:
            return False
        return bool(re.search(r"\d+(?:[.,]\d+)?", answer))


def _number_digits(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return _normalize_digits(str(value))


def _normalize_digits(value: str) -> str:
    return re.sub(r"[^0-9]", "", value or "")


def _asks_age_group_vote(question: str) -> bool:
    text = (question or "").lower()
    asks_vote = bool(re.search(r"votan|suelen votar|voto de|partido|que partido|qué partido", text))
    age_group = bool(re.search(r"joven|jóvenes|jovenes|mayores|mayores de \d{1,3}|menores de \d{1,3}|jubilad", text))
    return asks_vote and age_group
