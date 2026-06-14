from __future__ import annotations

import time
import logging
from typing import Any

from pydantic import ValidationError

from app.ask.tools_v2.errors import PendingToolError, UnknownToolError
from app.ask.tools_v2.registry import ToolRegistryV2
from app.ask.tools_v2.schemas import ToolContext, ToolResult


logger = logging.getLogger(__name__)


class ToolExecutorV2:
    def __init__(self, registry: ToolRegistryV2):
        self.registry = registry

    async def execute(self, tool_name: str, arguments: dict[str, Any], context: ToolContext | None = None) -> ToolResult:
        return self._execute_impl(tool_name, arguments, context)

    def execute_sync(self, tool_name: str, arguments: dict[str, Any], context: ToolContext | None = None) -> ToolResult:
        return self._execute_impl(tool_name, arguments, context)

    def _execute_impl(self, tool_name: str, arguments: dict[str, Any], context: ToolContext | None = None) -> ToolResult:
        started = time.monotonic()
        context = context or ToolContext()
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return self._controlled_result(UnknownToolError(), tool_name, "unknown_tool", "La herramienta solicitada no está activa.")
        status = getattr(tool, "status", "supported")
        if status == "pending" or status == "hidden":
            return self._controlled_result(PendingToolError(), tool_name, "pending_tool", "La herramienta solicitada no está activa.")
        try:
            payload = tool.input_schema.model_validate(arguments)
            raw_result = tool.execute(payload, context)
            result = ToolResult.model_validate(raw_result)
            result.metadata.update(self._context_metadata(context, arguments, result))
            self._log_execution(tool_name, result, context, started)
            return result
        except ValidationError:
            logger.info("ask_tool_v2_input_error", extra={"tool_name": tool_name})
            result = ToolResult(
                tool_name=tool_name,
                operation=tool_name,
                status="unsupported",
                methodology_plain="Los argumentos de la herramienta no son válidos.",
                caveats=["La herramienta no puede ejecutarse con esos argumentos."],
                metadata=self._context_metadata(context, arguments, None),
                error_code="invalid_tool_arguments",
                error_message="Los argumentos de la herramienta no son válidos.",
            )
            self._log_execution(tool_name, result, context, started)
            return result
        except Exception:
            logger.exception("ask_tool_v2_error", extra={"tool_name": tool_name})
            result = ToolResult(
                tool_name=tool_name,
                operation=tool_name,
                status="error",
                methodology_plain="He entendido la consulta, pero ahora mismo no puedo calcularla con las herramientas activas.",
                caveats=["El detalle técnico queda registrado internamente."],
                metadata=self._context_metadata(context, arguments, None),
                error_code="tool_execution_failed",
                error_message="No se ha podido ejecutar la herramienta.",
            )
            self._log_execution(tool_name, result, context, started)
            return result

    def _controlled_result(self, _error: Exception, tool_name: str, code: str, message: str) -> ToolResult:
        return ToolResult(
            tool_name=tool_name,
            operation=tool_name,
            status="unsupported",
            methodology_plain="He entendido la consulta, pero ahora mismo no puedo calcularla con las herramientas activas.",
            caveats=[message],
            error_code=code,
            error_message=message,
        )

    def _context_metadata(self, context: ToolContext, arguments: dict[str, Any], result: ToolResult | None) -> dict[str, Any]:
        rows = result.rows if result else []
        sections = [
            {"section_id": row.get("section_id"), "section_name": row.get("section_name")}
            for row in rows
            if row.get("section_id") or row.get("section_name")
        ][:20]
        return {
            "municipio_id": context.municipio_id,
            "municipio_nombre": context.municipio_nombre,
            "year": arguments.get("year") or arguments.get("target_year") or (rows[0].get("year") if rows else None),
            "start_year": arguments.get("start_year") or (rows[0].get("start_year") if rows else None),
            "end_year": arguments.get("end_year") or (rows[0].get("end_year") if rows else None),
            "metric": arguments.get("metric") or arguments.get("x_metric") or (result.metadata.get("metric") if result else None),
            "metric_label": (result.summary.get("value_label") if result else None) or (result.metadata.get("value_label") if result else None),
            "party": arguments.get("party") or (result.metadata.get("party") if result else None),
            "election_type": arguments.get("election_type"),
            "election_year": arguments.get("election_year"),
            "sections": sections,
        }

    def _log_execution(self, tool_name: str, result: ToolResult, context: ToolContext, started: float) -> None:
        logger.info(
            "ask_tool_v2_execute",
            extra={
                "tool_name": tool_name,
                "operation": result.operation,
                "status": result.status,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "rows_count": len(result.rows),
                "metric": result.metadata.get("metric"),
                "municipio_id": context.municipio_id,
            },
        )
