from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.services.orchestrator.context_store import OrchestratorConversationContext


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(ch for ch in normalized if not unicodedata.combining(ch)).split())


@dataclass(frozen=True, slots=True)
class MethodologyExplanation:
    intent: str
    answer: str


class MethodologyExplanationLayer:
    """Explains an existing analytical answer without requesting new data."""

    def explain(
        self, message: str, context: OrchestratorConversationContext
    ) -> MethodologyExplanation | None:
        if not should_handle_methodology_question(message, context):
            return None
        text = _normalize(message)
        intent = self._intent(text)
        assert intent is not None
        return MethodologyExplanation(intent=intent, answer=self._answer(intent, text, context))

    @staticmethod
    def _intent(text: str) -> str | None:
        if re.search(r"\b(lineage|linaje|historical sections?|seccion historica|secciones historicas)\b", text):
            return "lineage_definition"
        if re.search(r"\b(estimad[oa]|estimacion|proyeccion|oficial|fiable|fiabilidad|confianza|confiable|estimate|estimated|official|reliable|confidence)\b", text):
            return "confidence"
        if re.search(r"\b(que anos|que años|cuales anos|periodo|por que.*20\d{2}|comparad[oa].*anos|which years|what period|why.*20\d{2})\b", text):
            return "period"
        if re.search(r"\b(de donde|procedencia|fuente|datos? (?:has|han|utiliz)|origen (?:del|de ese)|donde.*numero|donde.*valor|where.*(?:value|number).*come|what data.*use|data provenance)\b", text):
            return "provenance"
        if re.search(r"\b(como.*calcul\w*|metodologia|metodo|formula|criterio|ordenad[oa]|obtuviste|llegaste.*resultado|how.*calculat\w*|methodology|method used|how.*obtain\w*)\b", text):
            return "calculation"
        if re.search(r"\b(que significa|como.*interpret\w*|explica|explicame|por que (?:esas|estas|elegiste|seleccionaste)|limitacion\w*|supuesto\w*|what does.*mean|how.*interpret\w*|explain|why (?:those|these)|limitations?|assumptions?)\b", text):
            return "interpretation"
        if text in {"por que", "por que?", "why", "explain"}:
            return "interpretation"
        return None

    def _answer(self, intent: str, text: str, context: OrchestratorConversationContext) -> str:
        variables = context.last_variables_used
        sources = context.last_source_views
        basis = context.last_ranking_basis or {}

        if intent == "lineage_definition":
            return (
                "El lineage es la relación histórica entre secciones censales a lo largo del tiempo. "
                "Los límites pueden cambiar, una sección puede dividirse o varias pueden agruparse.\n\n"
                "Cuando esa relación está disponible, la comparación reúne esos cambios administrativos para que "
                "el crecimiento represente evolución demográfica y no una alteración artificial de límites."
            )
        if intent == "period":
            years = sorted(set(re.findall(
                r"\b20\d{2}\b",
                context.last_answer_summary + " " + context.methodology_explanation.methodology,
            )))
            if len(years) >= 2:
                return (
                    f"Comparé {years[0]} con {years[-1]} porque ese era el periodo solicitado en la pregunta anterior.\n\n"
                    f"Para cada sección comparable, el cambio es la diferencia entre el valor inicial de {years[0]} "
                    f"y el valor final de {years[-1]}; el porcentaje se calcula respecto al valor inicial."
                )
            if years:
                return f"La respuesta anterior utilizó datos de {years[-1]}. No se hizo una comparación entre años."
            return "El periodo exacto no quedó registrado en el contexto de la respuesta anterior, así que no puedo afirmarlo con seguridad."
        if intent == "confidence":
            estimated = any(
                token in _normalize(" ".join(
                    context.methodology_explanation.warnings + [context.methodology_explanation.methodology]
                ))
                for token in ("estimacion", "estimado", "modelizad", "proyeccion")
            )
            if estimated:
                detail = next((
                    warning for warning in context.methodology_explanation.warnings
                    if "estim" in _normalize(warning)
                ), None)
                return (
                    "Sí, la respuesta anterior incluía un valor estimado o modelizado. "
                    + (f"La limitación registrada fue: {detail}." if detail else "No debe interpretarse como una medición individual ni una tasación oficial.")
                )
            if sources:
                return (
                    "No consta como una estimación en la respuesta anterior. Las cifras proceden de los datos "
                    "validados disponibles para el periodo consultado. Si una variable fuera proyectada o modelizada, lo indicaría expresamente."
                )
            return "El contexto anterior no conserva suficiente información de procedencia para confirmar si era una estimación."
        if intent == "provenance":
            if not sources:
                return "La respuesta anterior no conserva una fuente de datos identificable, así que no debo atribuirle una procedencia concreta."
            variable_text = ", ".join(variables) if variables else "las variables mostradas"
            return (
                f"El valor procede de los datos territoriales validados usados en la respuesta anterior para {variable_text}.\n\n"
                "La información estaba agregada por sección censal. No se utilizó información individual ni una fuente externa no indicada."
            )
        if intent == "calculation":
            methodology = context.methodology_explanation.methodology.strip()
            if methodology:
                answer = methodology
                replacements = {
                    "tool": "consulta analítica", "tools": "consultas analíticas",
                    "Orchestrator": "análisis", "orchestrator": "análisis",
                }
                for internal, public in replacements.items():
                    answer = answer.replace(internal, public)
                if not re.search(
                    r"\b(SQL|planner|API|endpoint|semantic catalog|rank_sections|agent_|vista(?:s)?|herramienta)\b|`",
                    answer,
                    flags=re.I,
                ):
                    return answer
            order = basis.get("variables") or variables
            if order:
                public_labels = {
                    "population_total": "la población total",
                    "population_growth_pct": "el porcentaje de crecimiento",
                    "population_absolute_change": "el cambio absoluto de población",
                    "population_under_30_pct": "el porcentaje de población menor de 30 años",
                    "population_density": "la densidad de población",
                    "abstention_pct": "el porcentaje de abstención",
                }
                criteria = ", ".join(public_labels.get(str(item), str(item).replace("_", " ")) for item in order)
                years = sorted(set(re.findall(r"\b20\d{2}\b", context.last_answer_summary)))
                period = f" para {years[-1]}" if len(years) == 1 else ""
                return (
                    f"Consulté los datos validados disponibles para cada sección censal{period} y apliqué el criterio solicitado sobre {criteria}. "
                    "Después ordené las secciones de mayor a menor y conservé las primeras posiciones mostradas en la respuesta. "
                    "No añadí valores externos ni estimaciones no indicadas."
                )
            return "El contexto conserva el resultado anterior, pero no una descripción metodológica suficiente para reconstruir el cálculo con precisión."
        if intent == "interpretation":
            reasons = basis.get("reason_for_top_sections") or []
            variables_text = ", ".join(str(value) for value in (basis.get("variables") or variables))
            answer = "La lectura anterior debe interpretarse como una comparación territorial agregada entre secciones censales."
            if variables_text:
                answer += f" La selección se basó en {variables_text}."
            if reasons:
                answer += " Las primeras secciones fueron las que obtuvieron los valores más altos según ese criterio."
            if context.methodology_explanation.warnings:
                answer += f" La principal limitación registrada fue: {context.methodology_explanation.warnings[0]}."
            return answer
        raise ValueError(f"Unsupported explanation intent: {intent}")


def should_handle_methodology_question(
    question: str,
    analytical_context: OrchestratorConversationContext | None,
) -> bool:
    """Conservative, side-effect-free Capability 01 activation guard."""
    if analytical_context is None or not analytical_context.last_tools_used:
        return False
    evidence = analytical_context.methodology_explanation
    if not (
        evidence.methodology.strip()
        or evidence.warnings
        or analytical_context.last_source_views
        or analytical_context.last_variables_used
        or analytical_context.last_ranking_basis
    ):
        return False

    text = _normalize(question)
    if MethodologyExplanationLayer._intent(text) is None:
        return False

    # Explanations may mention the already-used year ("why 2025?"). A bare/new
    # year request is analysis and must continue untouched through the old flow.
    has_year = bool(re.search(r"\b(?:19|20)\d{2}\b", text))
    explanatory_year = bool(re.search(
        r"\b(por que|why|usaste|utilizaste|elegiste|comparaste|which years|que anos|que periodo)\b",
        text,
    ))
    if has_year and not explanatory_year:
        return False

    new_analysis_patterns = (
        r"\b(recalcula|recalcular|calcula de nuevo|actualiza|actualizar|compara|comparar|comparalas|"
        r"lista|listar|ordena|ordenar|filtra|filtrar|agrega|agregar|recupera|recuperar|"
        r"muestra|mostrar|dame|busca|buscar|haz lo mismo|vuelve a calcular)\b",
        r"\b(y|ahora)\s+(en|para|con|por)\b",
        r"\b(cual|cuales)\b.*\b(mas|menos|mayor|menor|primera|ultima|ranking)\b",
        r"\b(otra|otro|nueva|nuevo)\s+(seccion|zona|metrica|periodo|ranking|comparacion)\b",
        r"\b(seccion|secciones)\s+\d{1,10}\b",
        r"\b(con|por)\s+(renta|ingresos?|poblacion|densidad|edad|abstencion|voto|vivienda|precio)\b",
    )
    if any(re.search(pattern, text) for pattern in new_analysis_patterns):
        return False

    # A named territory changes scope unless the question is defining lineage.
    if re.search(r"\b(riviera|calahonda|entrerrios|la cala|mijas pueblo|las lagunas)\b", text):
        if MethodologyExplanationLayer._intent(text) != "lineage_definition":
            return False
    return True
