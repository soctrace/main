from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from app.ask.llm.errors import LLMPlanningError, LLMSynthesisError, ProviderNotConfiguredError
from app.ask.llm.gemini_schema_adapter import parse_gemini_function_call, to_gemini_tools
from app.ask.llm.prompts import PLANNER_PROMPT, SYNTHESIS_PROMPT
from app.ask.llm.provider import LLMProvider
from app.ask.llm.schemas import (
    LLMComplexityLevel,
    LLMPlanRequest,
    LLMPlanResponse,
    LLMToolCall,
    LLMSynthesisRequest,
    LLMSynthesisResponse,
)
from app.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
        raise_on_missing_key: bool = True,
    ):
        self.settings = settings or get_settings()
        self.api_key = api_key if api_key is not None else self.settings.gemini_api_key
        self.client = client
        if not self.api_key and raise_on_missing_key:
            raise ProviderNotConfiguredError("GEMINI_API_KEY is missing")

    def _build_client(self) -> Any:
        try:
            from google import genai

            return genai.Client(api_key=self.api_key)
        except ImportError as exc:
            raise ProviderNotConfiguredError(
                "Gemini SDK missing.\n\n"
                "Run:\n\n"
                "pip install google-genai\n\n"
                "Then restart backend."
            ) from exc

    def _model_for_complexity(self, complexity: LLMComplexityLevel) -> str:
        if complexity == "simple":
            return self.settings.gemini_fast_model
        if complexity == "semi_complex":
            return self.settings.gemini_default_model
        if complexity == "complex":
            return self.settings.gemini_pro_model
        return self.settings.gemini_default_model

    async def plan(self, request: LLMPlanRequest) -> LLMPlanResponse:
        model = self._model_for_complexity(request.complexity)
        if self.client is None:
            self.client = self._build_client()

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self._generate_plan_response, model, request),
                timeout=self.settings.gemini_timeout_seconds,
            )
        except Exception as exc:
            logger.exception("Gemini planning failed")
            raise LLMPlanningError("Gemini planning failed") from exc

        tool_call = parse_gemini_function_call(response)
        if tool_call is None:
            return LLMPlanResponse(
                provider=self.name,
                model=model,
                tool_call=None,
                reasoning_summary="Gemini did not select a tool call.",
                confidence="low",
                raw=self._safe_raw_response(response),
            )

        return LLMPlanResponse(
            provider=self.name,
            model=model,
            tool_call=tool_call,
            reasoning_summary="Gemini selected tool via function calling.",
            confidence="medium",
            raw=self._safe_raw_response(response),
        )

    def _generate_plan_response(self, model: str, request: LLMPlanRequest) -> Any:
        gemini_tools = to_gemini_tools(request.tools)
        prompt = {
            "question": request.question,
            "conversation_context": request.conversation_context,
            "semantic_context": request.semantic_context,
            "locale": request.locale,
        }
        return self.client.models.generate_content(
            model=model,
            contents=json.dumps(prompt, ensure_ascii=False),
            config=self._generation_config(
                system_instruction=request.system_prompt or PLANNER_PROMPT,
                tools=gemini_tools,
                force_tool_call=bool(gemini_tools),
                response_mime_type=None,
            ),
        )

    async def synthesize(self, request: LLMSynthesisRequest) -> LLMSynthesisResponse:
        model = self.settings.gemini_default_model
        if self.client is None:
            self.client = self._build_client()

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self._generate_synthesis_response, model, request, True),
                timeout=self.settings.gemini_timeout_seconds,
            )
            parsed = self._parse_synthesis_response(response)
        except Exception as exc:
            logger.debug("Structured Gemini synthesis failed; falling back to text response: %s", exc)
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self._generate_synthesis_response, model, request, False),
                    timeout=self.settings.gemini_timeout_seconds,
                )
                parsed = {"answer": self._response_text(response)}
            except Exception as fallback_exc:
                logger.exception("Gemini synthesis failed")
                raise LLMSynthesisError("Gemini synthesis failed") from fallback_exc

        answer = parsed.get("answer") or self._deterministic_answer(request.tool_result)
        methodology = parsed.get("methodology") or request.tool_result.get("methodology_plain")
        short_caveat = parsed.get("short_caveat")
        suggested_followups = parsed.get("suggested_followups") or request.tool_result.get("suggested_followups") or []
        caveats = parsed.get("caveats") or request.tool_result.get("caveats") or []

        if self._has_obvious_inconsistency(answer, request.tool_result):
            logger.warning("Gemini synthesis failed numerical consistency guard")
            answer = self._deterministic_answer(request.tool_result)
            suggested_followups = request.tool_result.get("suggested_followups") or []
            caveats = request.tool_result.get("caveats") or []

        return LLMSynthesisResponse(
            provider=self.name,
            model=model,
            answer=answer,
            methodology=methodology,
            short_caveat=short_caveat,
            suggested_followups=list(suggested_followups),
            caveats=list(caveats),
            raw=self._safe_raw_response(response),
        )

    def _generate_synthesis_response(self, model: str, request: LLMSynthesisRequest, structured: bool) -> Any:
        prompt = {
            "question": request.question,
            "tool_result": request.tool_result,
            "conversation_context": request.conversation_context,
            "response_style": request.response_style,
            "locale": request.locale,
        }
        return self.client.models.generate_content(
            model=model,
            contents=json.dumps(prompt, ensure_ascii=False),
            config=self._generation_config(
                system_instruction=request.system_prompt or SYNTHESIS_PROMPT,
                tools=[],
                force_tool_call=False,
                response_mime_type="application/json" if structured else None,
            ),
        )

    def _generation_config(
        self,
        *,
        system_instruction: str,
        tools: list[Any],
        force_tool_call: bool,
        response_mime_type: str | None,
    ) -> Any:
        try:
            from google.genai import types

            config_kwargs: dict[str, Any] = {
                "system_instruction": system_instruction,
                "temperature": self.settings.gemini_temperature,
                "max_output_tokens": self.settings.gemini_max_output_tokens,
            }
            if tools:
                config_kwargs["tools"] = tools
                config_kwargs["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)
            if force_tool_call:
                config_kwargs["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="ANY")
                )
            if response_mime_type:
                config_kwargs["response_mime_type"] = response_mime_type
            return types.GenerateContentConfig(**config_kwargs)
        except Exception:
            config: dict[str, Any] = {
                "system_instruction": system_instruction,
                "temperature": self.settings.gemini_temperature,
                "max_output_tokens": self.settings.gemini_max_output_tokens,
            }
            if tools:
                config["tools"] = tools
            if response_mime_type:
                config["response_mime_type"] = response_mime_type
            return config

    def _extract_function_call(self, response: Any) -> dict[str, Any] | None:
        function_calls = getattr(response, "function_calls", None)
        if function_calls:
            return self._function_call_to_dict(function_calls[0])

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                function_call = getattr(part, "function_call", None)
                if function_call:
                    return self._function_call_to_dict(function_call)
        return None

    def _function_call_to_dict(self, function_call: Any) -> dict[str, Any]:
        name = getattr(function_call, "name", None)
        args = getattr(function_call, "args", None) or {}
        if isinstance(function_call, dict):
            name = function_call.get("name")
            args = function_call.get("args") or {}
        return {
            "name": str(name),
            "args": dict(args),
            "raw": self._object_to_dict(function_call),
        }

    def _parse_synthesis_response(self, response: Any) -> dict[str, Any]:
        text = self._response_text(response)
        if not text:
            raise LLMSynthesisError("Gemini synthesis response was empty")
        parsed = json.loads(_strip_json_fence(text))
        if not isinstance(parsed, dict):
            raise LLMSynthesisError("Gemini synthesis response was not an object")
        return parsed

    def _response_text(self, response: Any) -> str:
        text = getattr(response, "text", None)
        if text:
            return str(text).strip()
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            parts = getattr(getattr(candidate, "content", None), "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", None)
                if part_text:
                    return str(part_text).strip()
        return ""

    def _deterministic_answer(self, tool_result: dict[str, Any]) -> str:
        summary = tool_result.get("summary") or {}
        if summary.get("answer"):
            return str(summary["answer"])
        rows = tool_result.get("rows") or []
        if rows:
            first = rows[0]
            section = first.get("section_name") or first.get("name") or first.get("section_id") or "la primera sección"
            value = first.get("value")
            if value is not None:
                return f"El resultado principal es {section}, con valor {value}."
            return f"El resultado principal es {section}."
        return "He obtenido resultados estructurados de la herramienta, pero no hay una síntesis disponible."

    def _has_obvious_inconsistency(self, answer: str, tool_result: dict[str, Any]) -> bool:
        rows = tool_result.get("rows") or []
        if not rows:
            return False
        first = rows[0]
        expected_section = first.get("section_name") or first.get("name")
        expected_value = first.get("value")
        if expected_section and expected_section.lower() not in answer.lower():
            return True
        if expected_value is not None:
            normalized_answer = _normalize_number_text(answer)
            normalized_value = _normalize_number_text(str(expected_value))
            if normalized_value and normalized_value not in normalized_answer:
                return True
        return False

    def _safe_raw_response(self, response: Any) -> dict[str, Any] | None:
        raw = self._object_to_dict(response)
        return raw if isinstance(raw, dict) else None

    def _object_to_dict(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {key: self._object_to_dict(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._object_to_dict(item) for item in value]
        for method_name in ("model_dump", "to_json_dict"):
            method = getattr(value, method_name, None)
            if callable(method):
                try:
                    return method()
                except Exception:
                    pass
        return {"repr": repr(value)}

    def healthcheck(self) -> dict[str, Any]:
        health: dict[str, Any] = {
            "provider": self.name,
            "configured": bool(self.api_key),
            "models": {
                "simple": self.settings.gemini_fast_model,
                "semi_complex": self.settings.gemini_default_model,
                "complex": self.settings.gemini_pro_model,
            },
        }
        if not self.api_key:
            health["error"] = "GEMINI_API_KEY is missing"
        return health


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _normalize_number_text(value: str) -> str:
    return re.sub(r"[^0-9,-.]", "", value).replace(".", "").replace(",", ".")
