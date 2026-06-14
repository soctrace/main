from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from app.ask.llm.schemas import LLMSynthesisResponse
from app.ask.tools_v2.schemas import ToolResult


class GuardResult(BaseModel):
    ok: bool
    reasons: list[str] = Field(default_factory=list)


class AnswerGuard:
    def validate_tool_result(
        self,
        question: str,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_result: ToolResult,
    ) -> GuardResult:
        reasons: list[str] = []
        text = _normalize(question)
        rows = tool_result.rows or []

        if tool_result.status != "ok":
            reasons.append(f"tool status is {tool_result.status}")
        if _asks_for_sections(text) and rows and not any(row.get("section_name") for row in rows):
            reasons.append("section question without section_name rows")
        if _asks_for_ranking(text) and not rows:
            reasons.append("ranking question without rows")
        if _asks_for_party(text) and not (tool_args.get("party") or tool_result.metadata.get("party") or _rows_include_key(rows, "party")):
            reasons.append("party question without party context")
        if _asks_for_correlation(text) and tool_name == "correlation_analysis" and rows and not _rows_include_key(rows, "correlation"):
            reasons.append("correlation result without coefficient")
        if _asks_for_year(text) and not self._has_year_context(tool_result):
            reasons.append("year question without year metadata")
        if _asks_for_historical(text) and not self._has_historical_context(tool_result):
            reasons.append("historical question without historical context")
        if _asks_age_group_vote(text) and tool_name == "rank_sections":
            reasons.append("age-group voting question answered with demographic section ranking")

        return GuardResult(ok=not reasons, reasons=reasons)

    def validate_synthesis(
        self,
        question: str,
        tool_result: ToolResult,
        synthesis: LLMSynthesisResponse,
    ) -> GuardResult:
        reasons: list[str] = []
        answer = synthesis.answer or ""
        lowered = answer.lower()

        if re.search(r"\bselect\b|\bfrom\b|\bwhere\b|\bjoin\b|marts\.|agent_|ask_", lowered):
            reasons.append("answer exposes SQL or internal relation names")
        if _asks_age_group_vote(_normalize(question)):
            if "estimación territorial" not in lowered and "estimacion territorial" not in lowered:
                reasons.append("age-group voting answer omits territorial-estimation caveat")
            if "voto individual" not in lowered or "edad" not in lowered:
                reasons.append("age-group voting answer omits individual-vote caveat")

        rows = tool_result.rows or []
        if rows:
            first = rows[0]
            expected_section = first.get("section_name") or first.get("name")
            if expected_section and _asks_for_sections(_normalize(question)) and expected_section.lower() not in lowered:
                reasons.append("answer does not mention top section")
            expected_value = first.get("value")
            if expected_value is not None:
                value_text = _normalize_number(str(expected_value))
                if value_text and _contains_other_obvious_number(answer, value_text):
                    reasons.append("answer may contradict top value")

        return GuardResult(ok=not reasons, reasons=reasons)

    def _has_year_context(self, tool_result: ToolResult) -> bool:
        metadata = tool_result.metadata or {}
        if any(key in metadata for key in ("year", "start_year", "end_year", "election_year")):
            return True
        return any(any(key in row for key in ("year", "start_year", "end_year", "election_year")) for row in tool_result.rows)

    def _has_historical_context(self, tool_result: ToolResult) -> bool:
        metadata = tool_result.metadata or {}
        if metadata.get("elections_included") or metadata.get("start_year") or metadata.get("end_year"):
            return True
        return any(
            row.get("elections_included") or row.get("elections_checked") or row.get("start_year") or row.get("end_year")
            for row in tool_result.rows
        )


def _normalize(value: str) -> str:
    return value.lower()


def _asks_for_sections(text: str) -> bool:
    return bool(re.search(r"seccion|secciones|zona|zonas|donde|dónde", text))


def _asks_for_ranking(text: str) -> bool:
    return bool(re.search(r"ranking|mayor|menor|mas |más |top|secciones|zonas|donde|dónde", text))


def _asks_for_year(text: str) -> bool:
    return bool(re.search(r"\b20\d{2}\b|año|ano|desde|evolucion|evolución", text))


def _asks_for_party(text: str) -> bool:
    return bool(re.search(r"\bpp\b|\bpsoe\b|\bvox\b|partido|voto", text))


def _asks_for_historical(text: str) -> bool:
    return bool(re.search(r"histor|siempre|todas las elecciones", text))


def _asks_for_correlation(text: str) -> bool:
    return bool(re.search(r"correlaci|relacion|relación", text))


def _asks_age_group_vote(text: str) -> bool:
    asks_vote = bool(re.search(r"votan|suelen votar|voto de|partido|que partido|qué partido", text))
    age_group = bool(re.search(r"joven|jóvenes|jovenes|mayores|mayores de \d{1,3}|menores de \d{1,3}|jubilad", text))
    return asks_vote and age_group


def _rows_include_key(rows: list[dict[str, Any]], key: str) -> bool:
    return any(key in row and row.get(key) is not None for row in rows)


def _normalize_number(value: str) -> str:
    return re.sub(r"[^0-9]", "", value)


def _contains_other_obvious_number(answer: str, expected_digits: str) -> bool:
    if not expected_digits or expected_digits in _normalize_number(answer):
        return False
    numbers = re.findall(r"\d+(?:[.,]\d+)?", answer)
    return bool(numbers)
