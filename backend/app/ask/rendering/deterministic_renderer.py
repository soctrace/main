from __future__ import annotations

from typing import Any

from app.ask.rendering.answer_contract import AskRenderedAnswer, ResponseStyle
from app.ask.rendering.followups import normalize_followups
from app.ask.tools_v2.schemas import ToolResult


class DeterministicRenderer:
    async def render(
        self,
        question: str,
        tool_result: ToolResult,
        conversation_context: dict[str, Any],
        response_style: ResponseStyle = "detailed",
        locale: str = "es-ES",
    ) -> AskRenderedAnswer:
        rows = list(tool_result.rows or [])
        answer = self._answer(tool_result, response_style)
        return AskRenderedAnswer(
            answer=answer,
            mode=response_style,
            short_caveat=self._short_caveat(tool_result),
            methodology=tool_result.methodology_plain,
            caveats=list(tool_result.caveats or []),
            suggested_followups=normalize_followups(tool_result.suggested_followups),
            entities=self._entities(rows),
            table=self._table(tool_result, rows),
            chart_spec=tool_result.chart_spec,
            metadata={
                "renderer": "deterministic",
                "tool": tool_result.tool_name,
                "operation": tool_result.operation,
                "status": tool_result.status,
                **(tool_result.metadata or {}),
            },
        )

    def _answer(self, tool_result: ToolResult, response_style: ResponseStyle) -> str:
        if tool_result.status == "empty":
            return "He entendido la consulta, pero no hay datos que cumplan esos filtros."
        if tool_result.status == "unsupported":
            reason = self._safe_reason(tool_result)
            return "He entendido la consulta, pero ahora mismo no puedo calcularla con las herramientas activas." + reason
        if tool_result.status == "error":
            return "He entendido la consulta, pero ahora mismo no puedo calcularla con las herramientas activas."

        rows = list(tool_result.rows or [])
        if not rows:
            return "No hay resultados para la operación solicitada."
        first = rows[0]
        if tool_result.tool_name == "aggregate_municipality":
            return self._single_value_answer(tool_result, first)
        if tool_result.tool_name == "persistent_winner":
            return self._entity_list_answer(tool_result, rows)
        if tool_result.tool_name == "ecological_vote_profile_by_age_group":
            return self._age_vote_profile_answer(tool_result, rows)
        if tool_result.tool_name == "age_cohort_projection":
            return self._age_cohort_projection_answer(tool_result, rows)
        if tool_result.tool_name == "correlation_analysis":
            return self._correlation_answer(first)
        if tool_result.tool_name == "cross_metric_ranking":
            return self._cross_metric_answer(tool_result, rows)
        if tool_result.tool_name in {"compare_years", "population_growth"}:
            return self._comparison_answer(tool_result, first, rows, response_style)
        if len(rows) > 1 and self._looks_like_entity_list(tool_result):
            return self._ranking_answer(tool_result, rows, response_style)
        return self._single_result_answer(tool_result, first)

    def _single_result_answer(self, tool_result: ToolResult, first: dict[str, Any]) -> str:
        label = first.get("value_label") or tool_result.summary.get("value_label") or "valor"
        value = first.get("value")
        year = first.get("year") or tool_result.metadata.get("year")
        section = first.get("section_name") or first.get("name")
        if section and value is not None:
            return f"La sección destacada es {section}, con {_format_number(value)} {label}{_year_suffix(year)}."
        if section:
            return f"El resultado principal es {section}{_year_suffix(year)}."
        if value is not None:
            return f"El resultado municipal es {_format_number(value)} {label}{_year_suffix(year)}."
        return "He obtenido resultados estructurados para la consulta."

    def _single_value_answer(self, tool_result: ToolResult, first: dict[str, Any]) -> str:
        label = first.get("value_label") or tool_result.summary.get("value_label") or "valor"
        municipality = first.get("municipio_nombre") or tool_result.metadata.get("municipio_nombre") or "el municipio"
        value = first.get("value")
        return f"El valor municipal de {label} en {municipality} es {_format_number(value)}{_year_suffix(first.get('year'))}."

    def _ranking_answer(self, tool_result: ToolResult, rows: list[dict[str, Any]], response_style: ResponseStyle) -> str:
        first = rows[0]
        label = first.get("value_label") or tool_result.summary.get("value_label") or "valor"
        direct = f"La primera sección del ranking es {first.get('section_name')}, con {_format_number(first.get('value'))} {label}{_year_suffix(first.get('year'))}."
        if response_style == "simple":
            return direct
        bullets = "\n".join(
            f"• {idx}. {row.get('section_name')}: {_format_number(row.get('value'))} {row.get('value_label') or label}"
            for idx, row in enumerate(rows[:10], start=1)
        )
        return (
            direct
            + "\n\nResultados principales\n\n"
            + bullets
            + "\n\nQué significa\n\nEl ranking ordena las secciones según el valor observado de la métrica consultada.\n\n"
            + "Cómo se ha calculado\n\nUso la última observación disponible de las vistas aprobadas de soctrace y ordeno las secciones por esa variable.\n\n"
            + "Interpretación útil\n\nLas primeras posiciones señalan las zonas donde conviene mirar con más detalle para análisis territorial.\n\n"
            + "Cautela metodológica\n\n• Es una comparación por sección, no una medición individual.\n• Los resultados dependen del último año o elección disponible."
        )

    def _entity_list_answer(self, tool_result: ToolResult, rows: list[dict[str, Any]]) -> str:
        party = tool_result.metadata.get("party") or rows[0].get("party") or "El partido"
        exact = [row for row in rows if row.get("always_wins")]
        selected = exact or rows
        intro = f"{party} gana en todas las elecciones disponibles en {len(selected)} secciones:" if exact else f"No hay victorias persistentes completas; estas son las secciones más cercanas para {party}:"
        bullets = "\n".join(f"• {row.get('section_name')}" for row in selected[:20])
        return intro + ("\n\n" + bullets if bullets else "")

    def _age_vote_profile_answer(self, tool_result: ToolResult, rows: list[dict[str, Any]]) -> str:
        age_label = tool_result.metadata.get("age_group_label") or "este grupo de edad"
        year = rows[0].get("election_year") or tool_result.metadata.get("election_year")
        parties = [str(row.get("party")) for row in rows[:3] if row.get("party")]
        ranking = ", seguido de ".join([parties[0], " y ".join(parties[1:])]) if len(parties) > 1 else (parties[0] if parties else "sin partido destacado")
        bullets = "\n".join(
            f"• {row.get('party')}: {_format_number(row.get('weighted_vote_pct'))}%"
            for row in rows[:5]
        )
        return (
            f"Comparando las secciones con mayor peso de {age_label} con los resultados electorales disponibles"
            f"{_year_suffix(year)}, el partido con mayor asociación territorial en ese grupo es {ranking}.\n\n"
            "Resultados principales\n\n"
            f"{bullets}\n\n"
            "Qué significa\n\nNo puedo saber el voto individual por edad, porque el dataset no contiene voto individual por edad. Lo que sí puedo hacer es una estimación territorial.\n\n"
            "Cómo se ha calculado\n\nPondero el porcentaje de voto de cada partido en cada sección por el número estimado de personas del grupo de edad en esa sección.\n\n"
            "Cautela metodológica\n\n• No es voto individual por edad.\n• Es una lectura territorial por sección."
        )

    def _age_cohort_projection_answer(self, tool_result: ToolResult, rows: list[dict[str, Any]]) -> str:
        first = rows[0]
        label = first.get("value_label") or tool_result.summary.get("value_label") or "personas"
        total = first.get("municipality_total") or tool_result.summary.get("municipality_total")
        year = first.get("target_year") or first.get("year") or tool_result.metadata.get("target_year") or tool_result.metadata.get("year")
        direct = f"Total municipal estimado en Mijas: {_format_number(total)} {label}" if total is not None else f"Estas son las principales secciones para {label}"
        if year:
            direct += f" en {year}"
        bullets = "\n".join(
            f"• {row.get('section_name')}: {_format_number(row.get('value'))} {row.get('value_label') or label}"
            for row in rows[:5]
            if row.get("section_name")
        )
        return (
            direct
            + (".\n\nResultados principales\n\n" + bullets if bullets else ".")
            + "\n\nQué significa\n\nLa respuesta estima cuántas personas entran en la cohorte de edad consultada y dónde se concentran territorialmente.\n\n"
            + "Cómo se ha calculado\n\nUso la distribución por edad y sección del padrón disponible; si la edad cae dentro de una cohorte quinquenal, la cifra se prorratea dentro de esa cohorte.\n\n"
            + "Cautela metodológica\n\n• Es una estimación cuando la fuente agrupa edades.\n• No predice participación electoral ni comportamiento individual."
        )

    def _comparison_answer(self, tool_result: ToolResult, first: dict[str, Any], rows: list[dict[str, Any]], response_style: ResponseStyle) -> str:
        label = first.get("value_label") or tool_result.summary.get("value_label") or "valor"
        value = first.get("growth_abs", first.get("delta_abs", first.get("value")))
        direct = (
            f"Comparando {first.get('start_year')} con {first.get('end_year')}, "
            f"la zona destacada es {first.get('section_name')}, con una variación de {_format_number(value)} en {label}."
        )
        if response_style == "simple":
            return direct
        bullets = "\n".join(
            f"• {row.get('section_name')}: {_format_number(row.get('growth_abs', row.get('delta_abs', row.get('value'))))}"
            for row in rows[:10]
        )
        return (
            direct
            + ("\n\nResultados principales\n\n" + bullets if bullets else "")
            + "\n\nQué significa\n\nLa comparación muestra qué zonas cambian más entre los años disponibles.\n\n"
            + "Cómo se ha calculado\n\nComparo el valor inicial y final de cada sección o zona histórica y ordeno la variación.\n\n"
            + "Cautela metodológica\n\n• Los cambios de seccionado pueden afectar la comparación.\n• Cuando hay lineage disponible, soctrace agrupa secciones para reducir rupturas administrativas."
        )

    def _correlation_answer(self, first: dict[str, Any]) -> str:
        corr = first.get("correlation") or first.get("value")
        return (
            f"La correlación observada es {_format_number(corr)}. "
            "Es una lectura exploratoria por sección: no demuestra causalidad."
        )

    def _cross_metric_answer(self, tool_result: ToolResult, rows: list[dict[str, Any]]) -> str:
        first = rows[0]
        variables = tool_result.metric_explanations[:2]
        variable_label = " y ".join(item.label.lower() for item in variables) if variables else "los factores solicitados"
        variable_lines = "\n".join(
            f"• {item.label}: {item.plain_definition} {item.interpretation}"
            for item in variables
        )
        score = tool_result.score_explanation
        ranking = "\n".join(
            f"• {row.get('section_name')} — {_format_number(row.get('value'))}"
            for row in rows[:6]
        )
        return (
            f"La sección que mejor combina {variable_label} es {first.get('section_name')}.\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            f"Qué significa\n\nPara responder, combino estos factores:\n{variable_lines}\n\n"
            f"Cómo se ha calculado\n\n{score.score_name if score else 'Índice combinado'} va de {score.scale if score else '0 a 1'}. "
            f"{score.plain_definition if score else 'Cuanto más alto es, más intensa es la combinación territorial.'}\n\n"
            "Interpretación útil\n\nEstas zonas pueden ser relevantes para priorizar análisis territorial o acciones de movilización, porque concentran simultáneamente los factores consultados.\n\n"
            "Cautela metodológica\n\n• No demuestra causalidad.\n• No mide voto individual; es una lectura territorial por sección."
        )

    def _looks_like_entity_list(self, tool_result: ToolResult) -> bool:
        return tool_result.tool_name in {
            "rank_sections",
            "filter_sections",
            "party_strength",
            "historical_party_average",
            "cross_metric_ranking",
            "age_cohort_projection",
            "ecological_vote_profile_by_age_group",
        }

    def _entities(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "section",
                "id": row.get("section_id"),
                "name": row.get("section_name"),
                "value": row.get("value"),
                "valueLabel": row.get("value_label"),
            }
            for row in rows
            if row.get("section_id") and row.get("section_name")
        ]

    def _table(self, tool_result: ToolResult, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        table_rows = rows[:15]
        if not table_rows:
            return None
        columns = list(table_rows[0].keys())
        return {
            "title": tool_result.summary.get("value_label") or tool_result.operation,
            "columns": columns,
            "rows": [[row.get(column) for column in columns] for row in table_rows],
        }

    def _short_caveat(self, tool_result: ToolResult) -> str | None:
        return tool_result.caveats[0] if tool_result.caveats else None

    def _safe_reason(self, tool_result: ToolResult) -> str:
        if tool_result.error_code in {"unknown_tool", "pending_tool", "invalid_tool_arguments"}:
            return ""
        return f" {tool_result.caveats[0]}" if tool_result.caveats else ""


def _year_suffix(year: Any) -> str:
    return f" en {year}" if year is not None else ""


def _format_number(value: Any) -> str:
    if value is None:
        return "sin dato"
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}".replace(",", ".")
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(value)
