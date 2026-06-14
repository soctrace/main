from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.ask.semantic_layer import SemanticOperationInterpreter
from app.ask.suggestions.suggestion_registry import SuggestionRegistry
from app.ask.tools_v2 import ToolContext, ToolExecutorV2, ToolRegistryV2, tool_call_from_operation


logger = logging.getLogger(__name__)


class SuggestionValidationResult(BaseModel):
    question: str
    valid: bool
    status: Literal["ok", "unmapped", "unknown_tool", "empty", "error", "tool_mismatch"] = "error"
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    fallback_question: str | None = None
    reason: str | None = None


class SuggestionValidator:
    def __init__(
        self,
        *,
        registry: SuggestionRegistry,
        tool_registry: ToolRegistryV2,
        tool_executor: ToolExecutorV2,
        operation_interpreter: SemanticOperationInterpreter,
    ) -> None:
        self.registry = registry
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.operation_interpreter = operation_interpreter

    def validate(self, question: str, conversation_context: dict[str, Any] | None = None) -> SuggestionValidationResult:
        context = conversation_context or {}
        definition = self.registry.get(question)
        municipio_id = str(context.get("municipality") or context.get("activeMunicipality") or "29070")
        last_entities = context.get("last_entities") if isinstance(context.get("last_entities"), dict) else {}
        last_party = context.get("lastParty") or context.get("last_party") or last_entities.get("party")
        operation = self.operation_interpreter.interpret(
            question,
            municipio_id=municipio_id,
            active_year=context.get("activeYear"),
            last_metric=context.get("lastMetric") or context.get("last_metric"),
            last_party=last_party,
        )
        if not operation or not operation.supported:
            return SuggestionValidationResult(
                question=question,
                valid=False,
                status="unmapped",
                fallback_question=definition.fallback_question if definition else None,
                reason="semantic mapping not found",
            )
        tool_call = tool_call_from_operation(operation)
        if not tool_call:
            return SuggestionValidationResult(
                question=question,
                valid=False,
                status="unmapped",
                fallback_question=definition.fallback_question if definition else None,
                reason="tool call not resolved",
            )
        tool_name, arguments = tool_call
        if definition and definition.required_tool and definition.required_tool != tool_name:
            return SuggestionValidationResult(
                question=question,
                valid=False,
                status="tool_mismatch",
                tool_name=tool_name,
                arguments=arguments,
                fallback_question=definition.fallback_question,
                reason=f"expected {definition.required_tool}, got {tool_name}",
            )
        if self.tool_registry.get(tool_name) is None:
            return SuggestionValidationResult(
                question=question,
                valid=False,
                status="unknown_tool",
                tool_name=tool_name,
                arguments=arguments,
                fallback_question=definition.fallback_question if definition else None,
                reason="tool not registered",
            )
        try:
            result = self.tool_executor.execute_sync(
                tool_name,
                arguments,
                ToolContext(municipio_id=municipio_id, municipio_nombre="Mijas" if municipio_id == "29070" else None),
            )
        except Exception as exc:
            logger.info(
                "ask_suggestion_validation_failed",
                extra={"suggestion": question, "validation_status": "failed", "reason": str(exc)},
            )
            return SuggestionValidationResult(
                question=question,
                valid=False,
                status="error",
                tool_name=tool_name,
                arguments=arguments,
                fallback_question=definition.fallback_question if definition else None,
                reason=str(exc),
            )
        if result.status != "ok":
            return SuggestionValidationResult(
                question=question,
                valid=False,
                status="error",
                tool_name=tool_name,
                arguments=arguments,
                fallback_question=definition.fallback_question if definition else None,
                reason=result.error_message or result.status,
            )
        if not result.rows and int(result.summary.get("row_count") or 0) <= 0:
            return SuggestionValidationResult(
                question=question,
                valid=False,
                status="empty",
                tool_name=tool_name,
                arguments=arguments,
                fallback_question=definition.fallback_question if definition else None,
                reason="tool returned empty rows",
            )
        return SuggestionValidationResult(question=question, valid=True, status="ok", tool_name=tool_name, arguments=arguments)
