from __future__ import annotations

from typing import Any

from app.ask.tools_v2.schemas import ToolResult


def compress_tool_result_for_llm(tool_result: ToolResult, max_rows: int = 10) -> dict[str, Any]:
    rows = list(tool_result.rows or [])
    shown = rows[:max_rows]
    chart_summary = None
    if tool_result.chart_spec:
        chart_summary = {
            "type": tool_result.chart_spec.get("type"),
            "title": tool_result.chart_spec.get("title"),
            "x": tool_result.chart_spec.get("x"),
            "y": tool_result.chart_spec.get("y"),
            "rows_count": len(tool_result.chart_spec.get("rows") or []),
        }
    return {
        "tool_name": tool_result.tool_name,
        "operation": tool_result.operation,
        "status": tool_result.status,
        "summary": dict(tool_result.summary or {}),
        "rows": shown,
        "rows_shown": len(shown),
        "rows_total": len(rows),
        "truncated": len(rows) > len(shown),
        "metadata": _safe_metadata(tool_result.metadata),
        "chart_spec": chart_summary,
        "methodology_plain": tool_result.methodology_plain,
        "explanation": tool_result.explanation.model_dump() if tool_result.explanation else None,
        "metric_explanations": [item.model_dump() for item in tool_result.metric_explanations],
        "score_explanation": tool_result.score_explanation.model_dump() if tool_result.score_explanation else None,
        "caveats": list(tool_result.caveats or []),
        "suggested_followups": list(tool_result.suggested_followups or []),
        "sources": list(tool_result.sources or []),
        "error_code": tool_result.error_code,
    }


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    hidden = {"sql", "raw", "debug", "traceback", "exception"}
    return {key: value for key, value in (metadata or {}).items() if key.lower() not in hidden}
