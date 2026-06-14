from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from app.ask.conversation.conversation_state import ConversationState, LastAnswerContext
from app.services.local_analyst_service import normalize


FollowUpIntent = Literal[
    "confirm_year",
    "ask_year_used",
    "ask_period_used",
    "ask_methodology",
    "ask_table",
    "ask_percentage",
    "change_year",
    "ask_count",
    "compare_previous",
    "previous_sections_query",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class FollowUpResolution:
    intent: FollowUpIntent
    answer: str | None = None
    year: int | None = None
    rerun_question: str | None = None
    answer_prefix: str | None = None


class FollowUpResolver:
    def resolve(self, question: str, state: ConversationState | None) -> FollowUpResolution | None:
        if state is None or state.lastAnswerContext is None:
            return None
        context = state.lastAnswerContext
        text = normalize(question)

        year = self._year(question)
        if year and self._looks_like_year_confirmation(text):
            return FollowUpResolution("confirm_year", answer=self._confirm_year_answer(context, year), year=year)
        if year and self._looks_like_change_year(text):
            return FollowUpResolution(
                "change_year",
                year=year,
                rerun_question=self._question_with_year(context.question, year),
            )
        if self._asks_year_used(text):
            return FollowUpResolution("ask_year_used", answer=self._year_used_answer(context))
        if self._asks_period_used(text):
            return FollowUpResolution("ask_period_used", answer=self._period_answer(context))
        if self._asks_methodology(text):
            return FollowUpResolution("ask_methodology", answer=self._methodology_answer(context))
        if self._asks_table(text):
            return FollowUpResolution("ask_table", answer="Claro. Te dejo la tabla del resultado anterior.")
        if self._asks_percentage(text):
            rerun_question = self._question_with_relative_metric(context)
            prefix = None
            if context.metric in {"population_over_65", "population_under_30", "population_under_18", "population_total", "votes", "abstainers_count"}:
                prefix = "Tienes razón: la respuesta anterior mostraba el número absoluto. Si lo miramos en términos relativos,"
            return FollowUpResolution(
                "ask_percentage",
                rerun_question=rerun_question or self._question_with_percentage(context.question),
                answer_prefix=prefix,
            )
        if self._asks_count(text):
            return FollowUpResolution("ask_count", answer=self._count_answer(context))
        if self._mentions_previous_sections(text):
            return FollowUpResolution("previous_sections_query", answer=self._sections_answer(context))
        if self._compares_previous(text):
            return FollowUpResolution("compare_previous")
        return None

    def _year(self, question: str) -> int | None:
        match = re.search(r"\b(20\d{2}|19\d{2})\b", question)
        return int(match.group(1)) if match else None

    def _looks_like_year_confirmation(self, text: str) -> bool:
        return bool(re.search(r"\bson\b|\bes\b|\bera\b|\bcorresponden\b", text) and re.search(r"datos|dato|202\d|ano|año", text))

    def _looks_like_change_year(self, text: str) -> bool:
        return bool(re.search(r"^y\b|^¿?y\b|en\s+20\d{2}|para\s+20\d{2}", text))

    def _asks_year_used(self, text: str) -> bool:
        return bool(
            re.search(
                r"en que ano|en que año|que ano|qué año|de que ano|de que año|mas poblada en que ano|más poblada en qué año|"
                r"ese dato de que ano|ese dato de qué año|son datos de|ano son|año son|year",
                text,
            )
        )

    def _asks_period_used(self, text: str) -> bool:
        return bool(re.search(r"periodo|período|rango|entre que anos|entre qué años|comparado|comparaste|has comparado", text))

    def _asks_methodology(self, text: str) -> bool:
        return bool(re.search(r"como lo has calculado|cómo lo has calculado|como se calcula|metodolog|de donde sale|de dónde sale", text))

    def _asks_table(self, text: str) -> bool:
        return bool(re.search(r"\btabla\b|muestrame los datos|mu[eé]strame los datos|detalle", text))

    def _asks_percentage(self, text: str) -> bool:
        return bool(
            re.search(r"porcentaje|porcentual|relativo|valor relativo|peso relativo|proporcion|proporción|no absoluto|no en absoluto|%", text)
            and re.search(r"^y\b|^¿?y\b|me refiero|en porcentaje|porcentaje|relativo|no absoluto|no en absoluto", text)
        )

    def _asks_count(self, text: str) -> bool:
        return bool(re.search(r"cuantas son|cuántas son|cuantos son|cuántos son|cuantas secciones|cuántas secciones|numero de|número de", text))

    def _mentions_previous_sections(self, text: str) -> bool:
        return bool(re.search(r"esas secciones|estas secciones|las anteriores|esas zonas|estas zonas", text))

    def _compares_previous(self, text: str) -> bool:
        return bool(re.search(r"comparad|comparar|respecto a|frente a", text))

    def _confirm_year_answer(self, context: LastAnswerContext, requested_year: int) -> str:
        if context.startYear and context.endYear:
            return f"La respuesta anterior compara el periodo {context.startYear}-{context.endYear}."
        if context.year == requested_year:
            return f"Sí. Los datos que acabo de mostrar corresponden a {requested_year}, el último año disponible para esa variable en soctrace."
        if context.year:
            return f"No. La respuesta anterior usa datos de {context.year}. Si quieres, puedo recalcularlo para {requested_year} si esa variable está disponible."
        return "No puedo confirmarlo con precisión porque la respuesta anterior no dejó registrado un año único."

    def _year_used_answer(self, context: LastAnswerContext) -> str:
        if context.startYear and context.endYear:
            return f"Son datos comparados para el periodo {context.startYear}-{context.endYear}."
        if context.year:
            if context.metric == "population_total":
                return f"Ese dato corresponde a {context.year}, que es el último año disponible para población en el dataset."
            return f"Son datos de {context.year}."
        if context.election and context.election.year:
            return f"Usé la elección de {context.election.year}."
        return "La respuesta anterior no dejó registrado un año único; parece depender de una serie o histórico."

    def _period_answer(self, context: LastAnswerContext) -> str:
        if context.startYear and context.endYear:
            return f"He comparado el periodo {context.startYear}-{context.endYear}."
        if context.year:
            return f"No era una comparación temporal: usé datos de {context.year}."
        return "La respuesta anterior no registró un periodo temporal concreto."

    def _methodology_answer(self, context: LastAnswerContext) -> str:
        if context.methodologyPlain:
            return context.methodologyPlain
        metric = context.metricLabel or context.metric or "la métrica solicitada"
        return f"He ordenado el resultado anterior usando {metric} y los filtros de la consulta previa."

    def _count_answer(self, context: LastAnswerContext) -> str:
        rows = context.resultRows or []
        if context.operation == "party_always_wins_by_section":
            count = sum(1 for row in rows if row.get("always_wins"))
            if count:
                return f"Son {count} secciones."
        if context.sections:
            return f"Son {len(context.sections)} secciones en el resultado anterior."
        if rows:
            return f"Son {len(rows)} filas en el resultado anterior."
        return "No tengo un recuento estructurado del resultado anterior."

    def _sections_answer(self, context: LastAnswerContext) -> str:
        if context.sections:
            bullets = "\n".join(f"• {section.sectionName}" for section in context.sections[:20])
            return "Estas son las secciones del resultado anterior:\n\n" + bullets
        rows = context.resultRows or []
        names = [str(row.get("section_name") or row.get("sectionName")) for row in rows if row.get("section_name") or row.get("sectionName")]
        if names:
            bullets = "\n".join(f"• {name}" for name in names[:20])
            return "Estas son las secciones del resultado anterior:\n\n" + bullets
        return "No tengo secciones concretas guardadas para la respuesta anterior."

    def _question_with_year(self, question: str, year: int) -> str:
        cleaned = re.sub(r"\b(20\d{2}|19\d{2})\b", str(year), question, count=1)
        if cleaned != question:
            return cleaned
        return f"{question.rstrip(' ?¿')} en {year}"

    def _question_with_percentage(self, question: str) -> str:
        if re.search(r"porcentaje|%", normalize(question)):
            return question
        return f"{question.rstrip(' ?¿')} en porcentaje"

    def _question_with_relative_metric(self, context: LastAnswerContext) -> str | None:
        metric = context.metric
        if metric == "population_over_65":
            return "¿En qué sección hay mayor porcentaje de personas mayores de 65 años?"
        if metric == "population_under_30":
            return "¿En qué sección hay mayor porcentaje de población menor de 30 años?"
        if metric == "population_under_18":
            return "¿En qué sección hay mayor porcentaje de menores de 18 años?"
        if metric == "population_total":
            return "Ordena las secciones por densidad de población."
        if metric == "abstainers_count":
            return "¿Qué sección tiene mayor porcentaje de abstención?"
        if metric == "votes":
            party = f" al {context.party}" if context.party else ""
            return f"¿Dónde hay mayor porcentaje de voto{party}?"
        return None
