from __future__ import annotations

from typing import Any

from app.ask.semantic_layer import SemanticCatalog
from app.ask.explainability.response_explainer import ResponseExplainer
from app.ask.tools_v2.sql_builders import BuiltSql
from app.ask.tools_v2.schemas import ToolResult


class ResultNormalizer:
    def __init__(self, catalog: SemanticCatalog | None = None) -> None:
        self.catalog = catalog or SemanticCatalog()
        self.response_explainer = ResponseExplainer()

    def normalize(
        self,
        *,
        tool_name: str,
        operation: str,
        rows: list[dict[str, Any]],
        built: BuiltSql,
        chart_type: str | None = None,
        caveats: list[str] | None = None,
        methodology: str | None = None,
    ) -> ToolResult:
        metric_id = built.metadata.get("metric")
        metric = self.catalog.metric(metric_id)
        value_label = built.metadata.get("value_label") or (metric.label if metric else metric_id or "valor")
        normalized_rows = [self._normalize_row(row, value_label) for row in rows]
        status = "ok" if normalized_rows else "empty"
        summary = self._summary(normalized_rows, value_label)
        chart_spec = self._chart_spec(chart_type, normalized_rows, value_label)
        metadata = self._metadata(built.metadata, normalized_rows)
        explanation, metric_explanations, score_explanation = self.response_explainer.explain_tool_result(
            tool_name=tool_name,
            operation=operation,
            rows=normalized_rows,
            metadata=metadata,
        )
        return ToolResult(
            tool_name=tool_name,
            operation=operation,
            status=status,
            rows=normalized_rows,
            summary=summary,
            metadata=metadata,
            chart_spec=chart_spec,
            methodology_plain=methodology or self._methodology(operation, value_label),
            explanation=explanation,
            metric_explanations=metric_explanations,
            score_explanation=score_explanation,
            caveats=list(caveats or []) + list(metric.caveats if metric else []),
            suggested_followups=self._followups(operation, metric_id),
            sources=built.sources,
        )

    def _normalize_row(self, row: dict[str, Any], value_label: str) -> dict[str, Any]:
        result = dict(row)
        if "section_name" not in result and "lineage_group_name" in result:
            result["section_name"] = result["lineage_group_name"]
        if "value" not in result:
            for candidate in ("weighted_vote_pct", "growth_abs", "growth_pct", "delta_abs", "average_vote_pct", "correlation"):
                if candidate in result:
                    result["value"] = result[candidate]
                    break
        if "growth_abs" in result:
            result["growthAbs"] = result["growth_abs"]
        if "growth_pct" in result:
            result["growthPct"] = result["growth_pct"]
        if "target_age" in result and "target_year" in result and "value" in result:
            result["estimated_future_age_population"] = result["value"]
        result["value_label"] = value_label
        if "election_year" in result and "year" not in result:
            result["year"] = result["election_year"]
        return result

    def _metadata(self, metadata: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
        first = rows[0] if rows else {}
        sections = [
            {"section_id": row.get("section_id"), "section_name": row.get("section_name")}
            for row in rows
            if row.get("section_id") or row.get("section_name")
        ][:20]
        return {
            **metadata,
            "row_count": len(rows),
            "municipio_id": first.get("municipio_id") or metadata.get("municipio_id"),
            "municipio_nombre": first.get("municipio_nombre") or metadata.get("municipio_nombre"),
            "year": first.get("year") or metadata.get("year"),
            "start_year": first.get("start_year") or metadata.get("start_year"),
            "end_year": first.get("end_year") or metadata.get("end_year"),
            "election_year": first.get("election_year") or metadata.get("election_year"),
            "source_year": first.get("source_year") or metadata.get("source_year"),
            "target_year": first.get("target_year") or metadata.get("target_year"),
            "metric_label": metadata.get("value_label"),
            "sections": sections,
        }

    def _summary(self, rows: list[dict[str, Any]], value_label: str) -> dict[str, Any]:
        if not rows:
            return {"row_count": 0, "value_label": value_label}
        first = rows[0]
        return {
            "row_count": len(rows),
            "value_label": value_label,
            "top_section": first.get("section_name"),
            "top_value": first.get("value"),
            "year": first.get("year") or first.get("end_year") or first.get("target_year"),
            "municipality_total": first.get("municipality_total"),
        }

    def _chart_spec(self, chart_type: str | None, rows: list[dict[str, Any]], value_label: str) -> dict[str, Any] | None:
        if not rows or not chart_type:
            return None
        if chart_type == "metric":
            return {"type": "metric", "title": value_label, "value": rows[0].get("value"), "label": value_label, "rows": rows[:1]}
        if chart_type == "scatter":
            x_key = "x_value" if "x_value" in rows[0] else "value_1"
            y_key = "y_value" if "y_value" in rows[0] else "value_2"
            return {"type": "scatter", "title": value_label, "x": x_key, "y": y_key, "rows": rows}
        if chart_type == "line":
            return {"type": "line", "title": value_label, "x": "year", "y": "value", "rows": rows}
        if chart_type == "age_vote_profile":
            return {
                "type": "bar",
                "title": "Perfil electoral estimado por grupo de edad",
                "x": "party",
                "y": "weighted_vote_pct",
                "rows": rows,
            }
        return {"type": "bar", "title": value_label, "x": "section_name", "y": "value", "rows": rows}

    def _methodology(self, operation: str, value_label: str) -> str:
        return f"Ejecuto la herramienta universal `{operation}` sobre las vistas agent_* aprobadas y comparo {value_label}."

    def _followups(self, operation: str, metric_id: str | None) -> list[str]:
        if metric_id and metric_id.startswith("population"):
            return ["¿Qué secciones tienen mayor densidad de población?", "¿Qué zonas han crecido más?", "¿Qué secciones concentran más población joven?"]
        if operation == "rank_sections":
            return ["¿Qué zonas han crecido más?", "¿Qué secciones concentran más población joven?"]
        if operation in {"population_growth", "compare_years"}:
            return ["¿Puedes ordenar por porcentaje?", "¿Qué metodología has usado?"]
        if operation in {"party_strength", "persistent_winner"}:
            return ["¿Y el PSOE?", "¿Qué secciones son más disputadas?"]
        if operation == "ecological_vote_profile_by_age_group":
            return ["¿Puedes hacerlo para jóvenes?", "¿Qué secciones tienen mayor concentración de ese grupo?"]
        return ["¿Qué secciones tienen mayor población?", "¿Qué zonas han crecido más?"]
