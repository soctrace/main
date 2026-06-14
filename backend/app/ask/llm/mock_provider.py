from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.ask.llm.provider import LLMProvider
from app.ask.llm.schemas import (
    LLMPlanRequest,
    LLMPlanResponse,
    LLMToolCall,
    LLMSynthesisRequest,
    LLMSynthesisResponse,
)


def _normalize(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _extract_party(text: str) -> str | None:
    for party in ("PP", "PSOE", "VOX"):
        if re.search(rf"\b{party.lower()}\b", text):
            return party
    return None


class MockLLMProvider(LLMProvider):
    name = "mock"
    model = "mock-provider-v1"

    async def plan(self, request: LLMPlanRequest) -> LLMPlanResponse:
        question = _normalize(request.question)
        tool_call: LLMToolCall | None = None
        matched_rule = "none"

        if "gana siempre" in question:
            party = _extract_party(question)
            if party:
                matched_rule = "persistent_winner_party"
                tool_call = LLMToolCall(
                    tool_name="persistent_winner",
                    arguments={"party": party, "municipio_id": "29070"},
                )
        elif "jubilados" in question or "mayores de 65" in question:
            matched_rule = "retirees_age_proxy"
            tool_call = LLMToolCall(
                tool_name="rank_sections",
                arguments={
                    "metric": "population_over_65",
                    "order": "desc",
                    "limit": 5,
                    "municipio_id": "29070",
                },
            )
        elif "mas joven" in question or "seccion mas joven" in question:
            matched_rule = "youngest_section"
            tool_call = LLMToolCall(
                tool_name="rank_sections",
                arguments={
                    "metric": "average_age",
                    "order": "asc",
                    "limit": 1,
                    "municipio_id": "29070",
                },
            )
        elif "mayor poblacion" in question or "mas poblacion" in question or "mas habitantes" in question:
            matched_rule = "largest_population"
            tool_call = LLMToolCall(
                tool_name="rank_sections",
                arguments={
                    "metric": "population_total",
                    "order": "desc",
                    "limit": 1,
                    "municipio_id": "29070",
                },
            )

        return LLMPlanResponse(
            provider=self.name,
            model=self.model,
            tool_call=tool_call,
            reasoning_summary="Plan determinista del proveedor mock para validar el contrato LLM.",
            confidence="high" if tool_call else "low",
            raw={"matched_rule": matched_rule},
        )

    async def synthesize(self, request: LLMSynthesisRequest) -> LLMSynthesisResponse:
        summary = request.tool_result.get("summary") or {}
        answer = summary.get("answer")
        if not answer:
            answer = (
                "He ejecutado la operación solicitada y he obtenido resultados estructurados. "
                "La respuesta final se generará con el proveedor LLM real."
            )

        return LLMSynthesisResponse(
            provider=self.name,
            model=self.model,
            answer=answer,
            methodology=request.tool_result.get("methodology_plain"),
            short_caveat=(request.tool_result.get("caveats") or [None])[0],
            suggested_followups=list(request.tool_result.get("suggested_followups") or []),
            caveats=list(request.tool_result.get("caveats") or []),
            raw={"mock": True},
        )

    def healthcheck(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": True,
            "models": {},
        }
