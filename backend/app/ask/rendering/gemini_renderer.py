from __future__ import annotations

import logging
from typing import Any

from app.ask.llm.provider import LLMProvider
from app.ask.llm.schemas import LLMSynthesisRequest
from app.ask.rendering.answer_contract import AskRenderedAnswer, ResponseStyle
from app.ask.rendering.answer_guard import RenderAnswerGuard
from app.ask.rendering.deterministic_renderer import DeterministicRenderer
from app.ask.rendering.followups import normalize_followups
from app.ask.rendering.prompts import GEMINI_RENDERER_PROMPT
from app.ask.rendering.renderer import compress_tool_result_for_llm
from app.ask.tools_v2.schemas import ToolResult


logger = logging.getLogger(__name__)


class GeminiRenderer:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        deterministic_renderer: DeterministicRenderer | None = None,
        answer_guard: RenderAnswerGuard | None = None,
        max_rows_for_llm: int = 10,
    ) -> None:
        self.provider = provider
        self.deterministic_renderer = deterministic_renderer or DeterministicRenderer()
        self.answer_guard = answer_guard or RenderAnswerGuard()
        self.max_rows_for_llm = max_rows_for_llm

    async def render(
        self,
        question: str,
        tool_result: ToolResult,
        conversation_context: dict[str, Any],
        response_style: ResponseStyle = "detailed",
        locale: str = "es-ES",
    ) -> AskRenderedAnswer:
        fallback = await self.deterministic_renderer.render(
            question,
            tool_result,
            conversation_context,
            response_style=response_style,
            locale=locale,
        )
        if tool_result.status != "ok":
            return fallback

        compressed = compress_tool_result_for_llm(tool_result, max_rows=self.max_rows_for_llm)
        try:
            synthesis = await self.provider.synthesize(
                LLMSynthesisRequest(
                    question=question,
                    system_prompt=GEMINI_RENDERER_PROMPT,
                    tool_result=compressed,
                    conversation_context=conversation_context,
                    response_style=response_style,
                    locale=locale,
                )
            )
        except Exception:
            logger.exception("ask_gemini_renderer_failed", extra={"tool": tool_result.tool_name})
            fallback.metadata["renderer_fallback_reason"] = "provider_error"
            return fallback

        guard = self.answer_guard.validate(question=question, answer=synthesis.answer, tool_result=tool_result)
        if not guard.ok:
            logger.warning(
                "ask_gemini_renderer_guard_failed",
                extra={"tool": tool_result.tool_name, "reasons": guard.reasons},
            )
            fallback.metadata["renderer_fallback_reason"] = "guard_failed"
            fallback.metadata["renderer_guard_reasons"] = guard.reasons
            return fallback
        if not _has_result_first_order(synthesis.answer):
            logger.warning(
                "ask_gemini_renderer_order_failed",
                extra={"tool": tool_result.tool_name},
            )
            fallback.metadata["renderer_fallback_reason"] = "result_order_failed"
            return fallback

        return AskRenderedAnswer(
            answer=synthesis.answer,
            mode=response_style,
            short_caveat=synthesis.short_caveat or fallback.short_caveat,
            methodology=synthesis.methodology or tool_result.methodology_plain,
            caveats=list(synthesis.caveats or tool_result.caveats or []),
            suggested_followups=normalize_followups(synthesis.suggested_followups or tool_result.suggested_followups),
            entities=fallback.entities,
            table=fallback.table,
            chart_spec=tool_result.chart_spec,
            metadata={
                **(tool_result.metadata or {}),
                "renderer": "gemini",
                "provider": synthesis.provider,
                "model": synthesis.model,
                "tool": tool_result.tool_name,
                "operation": tool_result.operation,
                "compressed_rows_shown": compressed["rows_shown"],
                "compressed_rows_total": compressed["rows_total"],
                "compressed_truncated": compressed["truncated"],
            },
        )


def _has_result_first_order(answer: str) -> bool:
    text = answer or ""
    result_positions = [
        _heading_position(text, heading)
        for heading in ("Resultados principales", "Indicadores principales")
    ]
    result_positions = [position for position in result_positions if position >= 0]
    explanation_positions = [
        _heading_position(text, heading)
        for heading in ("Qué significa", "Que significa", "Cómo se ha calculado", "Como se ha calculado")
    ]
    explanation_positions = [position for position in explanation_positions if position >= 0]
    if not result_positions or not explanation_positions:
        return True
    return min(result_positions) < min(explanation_positions)


def _heading_position(text: str, heading: str) -> int:
    lowered = text.lower()
    return lowered.find(heading.lower())
