from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import Depends
from sqlalchemy.orm import Session

from app.ask.llm.errors import LLMProviderError
from app.ask.llm.factory import get_llm_provider
from app.ask.llm.schemas import LLMSynthesisRequest
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.repositories.analyst_repository import AnalystRepository
from app.services.analyst.composer import compose_final_answer, should_compose
from app.services.analyst.conversation_intelligence import (
    ConversationIntelligenceLayer,
    conversational_answer,
)
from app.services.analyst.dialogue_manager import ConsultativeDialogueManager, DialogueDecision
from app.services.analyst.evaluation import validate_response_grounding
from app.services.analyst.executive_reasoning import ExecutiveReasoningLayer
from app.services.analyst.memory import AnalystConversationMemory
from app.services.analyst.planner import PoliticalPlan, PoliticalPlanner
from app.services.analyst.political_rules import PoliticalClassificationEngine
from app.services.analyst.prompts import POLITICAL_ANALYST_SYSTEM_PROMPT
from app.services.analyst.schemas import (
    AnalystChart,
    AnalystChatRequest,
    AnalystChatResponse,
    AnalystSection,
    AnalystTable,
    StrategicRecommendation,
)
from app.services.analyst.synthetic_variables import CAMPAIGN_ROI_SCORE, TURNOUT_OPPORTUNITY_SCORE
from app.services.analyst.tools import AnalystToolResult, PoliticalAnalystTools
from app.services.analyst.workflows import PoliticalAnalystWorkflowExecutor, WorkflowOutput


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GroundingDecision:
    allowed: bool
    reason: str
    violations: list[str]


@dataclass(frozen=True, slots=True)
class AnalyticalRoute:
    intent: str
    workflow: str
    tool_name: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    clarification: str | None = None


class PoliticalAnalystAgent:
    _conversation_context: dict[str, dict[str, Any]] = {}

    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.tools = PoliticalAnalystTools(session)
        self.planner = PoliticalPlanner()
        self.workflow_executor = PoliticalAnalystWorkflowExecutor(self.tools)
        self.conversation_intelligence = ConversationIntelligenceLayer()
        self.dialogue_manager = ConsultativeDialogueManager()
        self.executive_reasoning = ExecutiveReasoningLayer()
        self.classifier = PoliticalClassificationEngine()
        self.audit_repository = AnalystRepository(session)

    async def chat(self, payload: AnalystChatRequest) -> AnalystChatResponse:
        if not self.settings.ask_analyst_enabled:
            return AnalystChatResponse(
                answer="El analista politico de soctrace no esta activado en este entorno.",
                methodology="Feature flag ASK_ANALYST_ENABLED=false.",
                confidence="low",
                warnings=["Ask Political Analyst is disabled by feature flag."],
                conversation_id=payload.conversation_id,
            )

        message = _sanitize(payload.message)
        municipality_id = payload.municipality_id
        conversation_id = payload.conversation_id or str(uuid4())
        dialogue_decision = self.dialogue_manager.decide(
            message,
            conversation_context=self._conversation_context.get(conversation_id),
            active_layer=payload.context.active_layer,
        )
        if dialogue_decision.dialogue_action in {"explain_capabilities", "ask_clarification", "answer_directly", "continue_previous_analysis"}:
            response = self._build_dialogue_response(dialogue_decision, message, conversation_id)
            response.audit_id = self._audit(message, municipality_id, f"dialogue:{dialogue_decision.dialogue_action}", None, response, tool_names=[])
            self._remember_dialogue_turn(conversation_id, message, dialogue_decision, response)
            return response

        analytical_route = self._analytical_route(message, payload.context.active_layer)
        if analytical_route:
            response = self._build_direct_analytical_response(
                route=analytical_route,
                municipality_id=municipality_id,
                conversation_id=conversation_id,
                year=payload.context.active_year,
            )
            response.audit_id = self._audit(
                message,
                municipality_id,
                analytical_route.intent,
                None,
                response,
                tool_names=response.tools_used,
            )
            return response

        conversation = self.conversation_intelligence.classify(message)
        if conversation.should_answer_without_tools:
            if conversation.user_intent == "contextual_follow_up":
                response = self._build_contextual_followup_response(message, conversation_id)
            else:
                response = self._build_conversational_response(message, conversation_id)
            response.audit_id = self._audit(message, municipality_id, "conversational", None, response, tool_names=[])
            return response
        plan = self.planner.plan(message, municipality_id)
        intent = plan.goal
        year = payload.context.active_year or 2023
        if plan.needs_clarification and plan.clarification_question:
            response = AnalystChatResponse(
                answer=plan.clarification_question,
                methodology=f"Clarificacion analitica: intent={intent}; no se activa general_territorial_advice.",
                confidence="medium",
                display_mode="chat",
                data_used=[],
                data_layers_used=[],
                tools_used=[],
                variables_used=[],
                sections=[],
                tables=[],
                charts=[],
                strategic_recommendations=[],
                follow_up_questions=[
                    "Cambio demográfico entre esos años",
                    "Cambio electoral entre esos años",
                    "Cambio de renta entre esos años",
                ],
                warnings=[],
                conversation_id=conversation_id,
            )
            response.audit_id = self._audit(message, municipality_id, intent, None, response, tool_names=[])
            return response

        try:
            workflow_output = self._execute_plan(plan, message, municipality_id, year, payload)
            tool_result = workflow_output.tool_result
            response = await self._build_response(
                intent=intent,
                message=message,
                municipality_id=municipality_id,
                conversation_id=conversation_id,
                tool_result=tool_result,
                plan=plan,
                tool_names=workflow_output.tool_names,
            )
            response.warnings.extend(validate_response_grounding(response))
            response.audit_id = self._audit(message, municipality_id, intent, tool_result, response, tool_names=workflow_output.tool_names)
            self._remember_turn(
                conversation_id=conversation_id,
                message=message,
                plan=plan,
                workflow_output=workflow_output,
                response=response,
            )
            return response
        except Exception as exc:
            logger.exception("Political analyst chat failed", extra={"intent": intent})
            self.session.rollback()
            response = AnalystChatResponse(
                answer=(
                    "Ahora mismo no puedo completar el análisis con todos los datos disponibles. "
                    "Puedo seguir con una recomendación más general si reformulas la pregunta."
                ),
                methodology="Respuesta segura sin inferir datos ausentes.",
                confidence="low",
                display_mode="chat",
                data_used=[],
                data_layers_used=[],
                tools_used=[],
                variables_used=[],
                warnings=[],
                conversation_id=conversation_id,
                follow_up_questions=[
                    "¿Dónde es más alta la abstención?",
                    "¿Qué secciones debería visitar primero el candidato?",
                ],
            )
            response.audit_id = self._audit(message, municipality_id, intent, None, response, error=str(exc))
            return response

    def _analytical_route(self, message: str, active_layer: str | None = None) -> AnalyticalRoute | None:
        text = _normalize(message)
        if re.search(r"\b(dime|di|sugiere|sugiereme|qué|que)\b.*\b(preguntas|puedo preguntarte|puedo hacerte)\b", text):
            return None

        year_pair = re.search(r"\b(20\d{2})\b.*\b(20\d{2})\b", text)
        change_question = bool(
            year_pair
            and re.search(r"\b(cambiaron|cambio|cambios|cambiar|variaron|vario|crecio|crecieron|subio|bajo)\b", text)
        )
        if change_question:
            start_year = int(year_pair.group(1))
            end_year = int(year_pair.group(2))
            layer = _normalize(active_layer or "")
            if any(token in layer for token in ("poblacion", "population", "demograf", "demographic")):
                return AnalyticalRoute(
                    intent="population_change_between_years",
                    workflow="demographic_metric_lookup",
                    tool_name="get_population_change_ranking",
                    start_year=start_year,
                    end_year=end_year,
                )
            if any(token in layer for token in ("electoral", "voto", "vote", "election")):
                return AnalyticalRoute(
                    intent="electoral_change_between_years",
                    workflow="electoral_metric_lookup",
                    tool_name="get_electoral_change_ranking",
                    start_year=start_year,
                    end_year=end_year,
                )
            if any(token in layer for token in ("renta", "income", "ingreso")):
                return AnalyticalRoute(
                    intent="income_change_between_years",
                    workflow="income_metric_lookup",
                    tool_name="get_income_change_ranking",
                    start_year=start_year,
                    end_year=end_year,
                )
            return AnalyticalRoute(
                intent="ambiguous_change_between_years",
                workflow="clarification",
                clarification=(
                    "¿Te refieres a cambio demográfico, cambio electoral o cambio de renta "
                    f"entre {start_year} y {end_year}?"
                ),
                start_year=start_year,
                end_year=end_year,
            )

        elderly_terms = re.search(r"\b(personas mayores|mayores|mayor de 65|mayores de 65|over 65|tercera edad)\b", text)
        max_terms = re.search(r"\b(cual|que seccion|donde hay|donde|mayor|mas|más)\b", text)
        if elderly_terms and max_terms:
            return AnalyticalRoute(
                intent="elderly_population_max_section",
                workflow="age_structure_metric_lookup",
                tool_name="get_age_structure",
            )

        if re.search(r"(seccion mas joven|seccion con menor edad|mas joven|poblacion mas joven)", text):
            return AnalyticalRoute(
                intent="youngest_section",
                workflow="age_structure_metric_lookup",
                tool_name="get_age_structure",
            )

        if re.search(
            r"(seccion con mayor poblacion|seccion mas poblada|seccion electoral mas poblada|"
            r"seccion tiene mas habitantes|mayor numero de habitantes|mayor poblacion|mas poblacion|mas habitantes)",
            text,
        ):
            return AnalyticalRoute(
                intent="population_max_section",
                workflow="demographic_metric_lookup",
                tool_name="get_population_ranking",
            )

        if re.search(r"(donde hay mas abstencion|donde hay mayor abstencion|mayor abstencion|mas abstencion)", text):
            return AnalyticalRoute(
                intent="abstention_max_section",
                workflow="electoral_metric_lookup",
                tool_name="get_turnout_analysis",
            )

        if re.search(r"(donde (gano|gana|crecio|cambio)|que secciones (gano|ganaron|crecieron|cambiaron)|cambio mas el voto)", text):
            return AnalyticalRoute(
                intent="electoral_metric_clarification",
                workflow="clarification",
                clarification=(
                    "Puedo responderlo como consulta electoral, pero necesito concretar la métrica: "
                    "partido, participación, abstención o cambio de voto entre dos años."
                ),
            )

        if re.search(r"^\s*(cual|que seccion|donde hay mas|donde hay mayor|que secciones cambiaron)\b", text):
            return AnalyticalRoute(
                intent="analytical_clarification",
                workflow="clarification",
                clarification=(
                    "Puedo responderlo como consulta analítica, pero necesito concretar la métrica: "
                    "población, edad, abstención, voto, renta o crecimiento."
                ),
            )
        return None

    def _build_direct_analytical_response(
        self,
        *,
        route: AnalyticalRoute,
        municipality_id: str,
        conversation_id: str,
        year: int | None,
    ) -> AnalystChatResponse:
        if route.clarification and not route.tool_name:
            return AnalystChatResponse(
                answer=route.clarification,
                methodology=f"Direct analytical intent guard: intent={route.intent}; workflow={route.workflow}; no fallback workflow activated.",
                confidence="medium",
                display_mode="chat",
                data_used=[],
                data_layers_used=[],
                tools_used=[],
                variables_used=[],
                sections=[],
                tables=[],
                charts=[],
                strategic_recommendations=[],
                follow_up_questions=[
                    "Cambio demográfico entre esos años",
                    "Cambio electoral entre esos años",
                    "Cambio de renta entre esos años",
                ],
                warnings=[],
                conversation_id=conversation_id,
            )

        if route.intent == "population_max_section":
            result = self.tools.get_population_ranking(municipality_id, year=year, limit=1)
            answer = self._population_max_answer(result)
            return self._metric_lookup_response(
                route=route,
                result=result,
                answer=answer,
                conversation_id=conversation_id,
                table_title="Sección con mayor población",
                table_columns=["Seccion", "Poblacion", "Densidad", "Año"],
                table_keys=["section_name", "population_total", "population_density", "year"],
            )

        if route.intent == "elderly_population_max_section":
            result = self.tools.get_elderly_population_ranking(municipality_id, year=year, limit=1)
            answer = self._elderly_population_max_answer(result)
            return self._metric_lookup_response(
                route=route,
                result=result,
                answer=answer,
                conversation_id=conversation_id,
                table_title="Sección con mayor número de personas mayores",
                table_columns=["Seccion", "Personas mayores", "% mayores", "Poblacion", "Año"],
                table_keys=["section_name", "elderly_population", "over_65_pct", "population_total", "year"],
            )

        if route.intent == "youngest_section":
            result = self.tools.get_age_structure(municipality_id, limit=1, youngest=True)
            answer = self._youngest_section_answer(result)
            return self._metric_lookup_response(
                route=route,
                result=result,
                answer=answer,
                conversation_id=conversation_id,
                table_title="Sección más joven",
                table_columns=["Seccion", "Edad media", "% menores de 30", "% mayores"],
                table_keys=["section_name", "average_age", "under_30_pct", "over_65_pct"],
            )

        if route.intent == "abstention_max_section":
            result = self.tools.get_turnout_analysis(municipality_id, year=year or 2023, limit=1)
            answer = self._abstention_max_answer(result, year or 2023)
            return self._metric_lookup_response(
                route=route,
                result=result,
                answer=answer,
                conversation_id=conversation_id,
                table_title="Sección con mayor abstención",
                table_columns=["Seccion", "Abstencion", "Censo", "Votos emitidos"],
                table_keys=["section_name", "abstention_rate_pct", "censo", "votos_emitidos"],
            )

        if route.intent == "population_change_between_years":
            result = self.tools.get_population_change_ranking(
                municipality_id,
                start_year=route.start_year or 2019,
                end_year=route.end_year or 2023,
                limit=8,
            )
            answer = self._population_change_answer(result, route.start_year or 2019, route.end_year or 2023)
            return self._metric_lookup_response(
                route=route,
                result=result,
                answer=answer,
                conversation_id=conversation_id,
                table_title="Secciones con mayor cambio de población",
                table_columns=["Seccion", "Inicio", "Final", "Cambio", "% cambio"],
                table_keys=["section_name", "population_start", "population_end", "population_change", "population_change_pct"],
            )

        if route.intent == "electoral_change_between_years":
            result = self.tools.get_electoral_change_ranking(
                municipality_id,
                start_year=route.start_year or 2019,
                end_year=route.end_year or 2023,
                limit=8,
            )
            answer = self._electoral_change_answer(result, route.start_year or 2019, route.end_year or 2023)
            return self._metric_lookup_response(
                route=route,
                result=result,
                answer=answer,
                conversation_id=conversation_id,
                table_title="Secciones con mayor cambio electoral",
                table_columns=["Seccion", "Participacion inicial", "Participacion final", "Cambio participacion", "Cambio abstencion"],
                table_keys=["section_name", "turnout_start", "turnout_end", "turnout_change_pct", "abstention_change_pct"],
            )

        if route.intent == "income_change_between_years":
            result = self.tools.get_income_change_ranking(
                municipality_id,
                start_year=route.start_year or 2019,
                end_year=route.end_year or 2023,
                limit=8,
            )
            answer = self._income_change_answer(result, route.start_year or 2019, route.end_year or 2023)
            return self._metric_lookup_response(
                route=route,
                result=result,
                answer=answer,
                conversation_id=conversation_id,
                table_title="Secciones con mayor cambio de renta",
                table_columns=["Seccion", "Renta inicial", "Renta final", "Cambio renta", "% cambio"],
                table_keys=["section_name", "individual_income_start", "individual_income_end", "individual_income_change", "individual_income_change_pct"],
            )

        return AnalystChatResponse(
            answer=route.clarification or "Necesito concretar la métrica antes de hacer un ranking territorial.",
            methodology=f"Direct analytical intent guard: intent={route.intent}; workflow={route.workflow}; no fallback workflow activated.",
            confidence="medium",
            display_mode="chat",
            warnings=[],
            conversation_id=conversation_id,
        )

    def _metric_lookup_response(
        self,
        *,
        route: AnalyticalRoute,
        result: AnalystToolResult,
        answer: str,
        conversation_id: str,
        table_title: str,
        table_columns: list[str],
        table_keys: list[str],
    ) -> AnalystChatResponse:
        sections = self._sections_from_rows(result.rows)
        tables = [
            AnalystTable(
                title=table_title,
                columns=table_columns,
                rows=[
                    [_format_cell(row.get(key), key=key) for key in table_keys]
                    for row in result.rows
                ],
            )
        ] if result.rows else []
        charts = [self._chart_from_rows(route.intent, result.rows)] if result.rows else []
        return AnalystChatResponse(
            answer=answer,
            methodology=(
                f"Direct analytical intent guard: intent={route.intent}; workflow={route.workflow}; "
                f"tool={route.tool_name}; no fallback workflow activated. {result.methodology}"
            ),
            confidence="high" if result.rows else "low",
            display_mode="structured" if result.rows else "chat",
            data_used=result.data_used,
            data_layers_used=_data_layers(result.data_used),
            tools_used=[result.name],
            variables_used=_variables_used(result.rows),
            sections=sections,
            tables=tables,
            charts=charts,
            strategic_recommendations=[],
            follow_up_questions=[
                "¿Quieres ver el ranking completo de secciones?",
                "¿Quieres comparar esta sección con la media municipal?",
                "¿Quieres cruzarlo con renta, edad o voto?",
            ],
            warnings=_public_warnings(result.warnings),
            conversation_id=conversation_id,
        )

    def _population_max_answer(self, result: AnalystToolResult) -> str:
        if not result.rows:
            return "No encuentro una sección con población total disponible para esa consulta."
        row = result.rows[0]
        section = row.get("section_name") or row.get("section_id") or "la sección principal"
        year = row.get("year") or "el año disponible"
        population = _fmt_int(row.get("population_total"))
        return f"La sección con mayor población de Mijas es {section}, con {population} habitantes en {year}."

    def _elderly_population_max_answer(self, result: AnalystToolResult) -> str:
        if not result.rows:
            return "No encuentro datos de estructura de edad suficientes para calcular la sección con más personas mayores."
        row = result.rows[0]
        section = row.get("section_name") or row.get("section_id") or "la sección principal"
        year = row.get("year") or "el año disponible"
        elderly = _fmt_int(row.get("elderly_population"))
        pct = _pct(row.get("over_65_pct"))
        return f"La sección con mayor número de personas mayores de Mijas es {section}, con {elderly} personas mayores ({pct}) en {year}."

    def _youngest_section_answer(self, result: AnalystToolResult) -> str:
        if not result.rows:
            return "No encuentro datos de estructura de edad suficientes para calcular la sección más joven."
        row = result.rows[0]
        section = row.get("section_name") or row.get("section_id") or "la sección principal"
        average_age = _fmt(row.get("average_age"))
        under_30 = _pct(row.get("under_30_pct"))
        return f"La sección más joven de Mijas es {section}, con edad media {average_age} y {under_30} de población menor de 30 años."

    def _abstention_max_answer(self, result: AnalystToolResult, year: int) -> str:
        if not result.rows:
            return f"No encuentro datos de abstención suficientes para {year}."
        row = result.rows[0]
        section = row.get("section_name") or row.get("section_id") or "la sección principal"
        abstention = _pct(row.get("abstention_rate_pct"))
        return f"La sección con mayor abstención de Mijas es {section}, con {abstention} en {year}."

    def _population_change_answer(self, result: AnalystToolResult, start_year: int, end_year: int) -> str:
        if not result.rows:
            return f"No encuentro datos suficientes para comparar población entre {start_year} y {end_year}."
        names = ", ".join(str(row.get("section_name") or row.get("section_id")) for row in result.rows[:3])
        return f"Las secciones con mayor cambio demográfico entre {start_year} y {end_year} son: {names}."

    def _electoral_change_answer(self, result: AnalystToolResult, start_year: int, end_year: int) -> str:
        if not result.rows:
            return f"No encuentro datos suficientes para comparar cambio electoral entre {start_year} y {end_year}."
        first = result.rows[0]
        section = first.get("section_name") or first.get("section_id") or "la sección principal"
        change = _pct(first.get("turnout_change_pct"))
        return f"La sección con mayor cambio electoral entre {start_year} y {end_year} es {section}, con un cambio de participación de {change}."

    def _income_change_answer(self, result: AnalystToolResult, start_year: int, end_year: int) -> str:
        if not result.rows:
            return f"No encuentro datos suficientes para comparar renta entre {start_year} y {end_year}."
        first = result.rows[0]
        section = first.get("section_name") or first.get("section_id") or "la sección principal"
        change = _fmt_int(first.get("individual_income_change"))
        return f"La sección con mayor cambio de renta entre {start_year} y {end_year} es {section}, con una variación de {change} EUR por persona."

    def _execute_plan(
        self,
        plan: PoliticalPlan,
        message: str,
        municipality_id: str,
        year: int,
        payload: AnalystChatRequest,
    ) -> WorkflowOutput:
        workflow_output = self.workflow_executor.run(plan, year=year)
        if workflow_output.tool_result.rows or workflow_output.tool_names:
            return workflow_output
        if plan.domain not in {"electoral", "electoral_strategy"}:
            return workflow_output
        intent = self._legacy_intent(plan.goal, message)
        party = plan.target_party or _extract_party(message)
        if intent == "abstention":
            result = self.tools.get_turnout_analysis(municipality_id, year=year, limit=8)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if intent == "candidate_visit":
            result = self.tools.build_campaign_recommendation(municipality_id, target_party=party, year=year)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if intent == "opportunity":
            result = self.tools.rank_sections_by_opportunity(municipality_id, target_party=party, year=year)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if intent == "dhondt":
            result = self.tools.calculate_dhondt(municipality_id, year=year)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if intent == "age":
            result = self.tools.get_age_structure(municipality_id, youngest=not _is_aging_question(message))
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if intent == "income":
            result = self.tools.get_income_profile(municipality_id, year=year)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if intent == "population_growth":
            result = self.tools.get_population_trend(municipality_id, year=year)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if intent == "population_ranking":
            result = self.tools.get_population_ranking(municipality_id, year=year)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if intent == "section_profile":
            section_id = payload.context.selected_section_id or _extract_section_id(message)
            if section_id:
                result = self.tools.get_section_profile(municipality_id, section_id=section_id, year=year)
                return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
            result = self.tools.rank_sections_by_opportunity(municipality_id, target_party=party, year=year, limit=5)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if intent == "land_built":
            result = self.tools.get_land_built_profile(municipality_id, year=year)
            return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)
        if intent == "general_territorial_advice":
            return workflow_output
        result = self.tools.get_election_results(municipality_id, party=party, year=year, limit=8)
        return WorkflowOutput(tool_result=result, tool_names=[result.name], plan=plan)

    async def _build_response(
        self,
        *,
        intent: str,
        message: str,
        municipality_id: str,
        conversation_id: str,
        tool_result: AnalystToolResult,
        plan: PoliticalPlan | None = None,
        tool_names: list[str] | None = None,
    ) -> AnalystChatResponse:
        sections = self._sections_from_rows(tool_result.rows)
        tables = [self._table_from_rows(intent, tool_result.rows)] if tool_result.rows else []
        charts = [self._chart_from_rows(intent, tool_result.rows)] if tool_result.rows else []
        recommendations = self._recommendations(intent, sections)
        synthetic_used = []
        if intent in {"candidate_visit", "opportunity", "abstention", "campaign_plan", "candidate_visit_plan", "abstention_analysis", "party_growth_opportunity"}:
            synthetic_used.append(TURNOUT_OPPORTUNITY_SCORE)
        if intent in {"candidate_visit", "opportunity", "campaign_plan", "candidate_visit_plan", "party_growth_opportunity"}:
            synthetic_used.append(CAMPAIGN_ROI_SCORE)

        deterministic_answer = self._deterministic_answer(intent, tool_result, sections, plan)
        methodology = tool_result.methodology
        warnings = _public_warnings(tool_result.warnings)
        follow_up_questions = self._follow_ups(intent)
        executive = self.executive_reasoning.reason(
            message=message,
            plan=plan,
            tool_result=tool_result,
            sections=sections,
        )

        composed = None
        if should_compose(intent):
            composed = compose_final_answer(
                message=message,
                intent=intent,
                plan=plan,
                tool_result=tool_result,
                sections=sections,
                executive_reasoning=executive,
            )
            deterministic_answer = composed.answer
            tables = composed.tables
            recommendations = composed.recommendations
            follow_up_questions = composed.follow_up_questions
            warnings = _public_warnings([*warnings, *composed.warnings])

        if composed is None:
            llm_answer = await self._try_llm_synthesis(
                message=message,
                tool_result=tool_result,
                fallback_answer=deterministic_answer,
                fallback_methodology=methodology,
                conversation_id=conversation_id,
                plan=plan,
            )
            if llm_answer:
                deterministic_answer = llm_answer.get("answer") or deterministic_answer
                methodology = llm_answer.get("methodology") or methodology
                warnings.extend(llm_answer.get("warnings", []))

        if municipality_id != "29070":
            warnings.append("Phase 1 currently has validated data coverage for Mijas only.")

        return AnalystChatResponse(
            answer=deterministic_answer,
            methodology=methodology,
            confidence="high" if tool_result.rows else "low",
            display_mode="chat" if composed is not None else "structured",
            data_used=tool_result.data_used,
            data_layers_used=_data_layers(tool_result.data_used),
            tools_used=tool_names or [],
            variables_used=_variables_used(tool_result.rows),
            executive_thesis=executive.executive_thesis if composed is not None else None,
            priority_sections=composed.priority_sections if composed is not None else [],
            recommendations=[item.model_dump() for item in recommendations] if composed is not None else [],
            evidence_table=composed.evidence_table if composed is not None else [],
            limitations=composed.limitations if composed is not None else [],
            sections=sections,
            tables=tables,
            charts=charts,
            synthetic_variables_used=[] if composed is not None else synthetic_used,
            synthetic_variables_created=[],
            strategic_recommendations=recommendations,
            follow_up_questions=follow_up_questions[:3],
            warnings=warnings,
            conversation_id=conversation_id,
        )

    def _build_conversational_response(self, message: str, conversation_id: str) -> AnalystChatResponse:
        answer, follow_ups = conversational_answer(message)
        return AnalystChatResponse(
            answer=answer,
            methodology="",
            confidence="high",
            display_mode="chat",
            data_used=[],
            data_layers_used=[],
            tools_used=[],
            variables_used=[],
            sections=[],
            tables=[],
            charts=[],
            strategic_recommendations=[],
            follow_up_questions=follow_ups[:3],
            warnings=[],
            conversation_id=conversation_id,
        )

    def _build_contextual_followup_response(self, message: str, conversation_id: str) -> AnalystChatResponse:
        context = self._conversation_context.get(conversation_id)
        if not context:
            return AnalystChatResponse(
                answer=(
                    "No tengo una recomendación anterior en esta conversación para auditar. "
                    "Pregúntame primero por una decisión territorial y después puedo explicarte capas, variables y limitaciones."
                ),
                methodology="",
                confidence="medium",
                display_mode="chat",
                data_used=[],
                data_layers_used=[],
                tools_used=[],
                variables_used=[],
                follow_up_questions=[
                    "¿Qué zonas priorizarías para una formación laboral?",
                    "¿Qué datos usarías para una campaña de ayudas a desempleados?",
                ],
                warnings=[],
                conversation_id=conversation_id,
            )

        text = _normalize(message)
        layers = context.get("last_data_layers_used", [])
        variables = context.get("last_variables_used", [])
        tools = context.get("last_tools_used", [])
        limitations = context.get("last_limitations", [])
        sections = context.get("last_sections_recommended", [])
        used_socioeconomic = "Socioeconomic Intelligence" in layers

        data_layers_text = ", ".join(layers) if layers else "ninguna capa registrada"
        tools_text = ", ".join(tools) if tools else "ninguna herramienta registrada"
        variables_text = ", ".join(variables[:12]) if variables else "no hay variables detalladas registradas en memoria."
        sections_text = ", ".join(sections[:5]) if sections else "no hay secciones recomendadas registradas en memoria."
        limitations_text = "; ".join(limitations) if limitations else "sin limitaciones relevantes registradas."

        if "socioeconom" in text or "inteligencia socioeconomica" in text:
            if used_socioeconomic:
                answer = (
                    "Sí. En la recomendación anterior usé la capa de Inteligencia Socioeconómica "
                    "junto con capas territoriales como población, densidad, renta y estructura de edad. "
                    "El ranking combinó señales de potencial productivo, empleo/desempleo, ocupación y actividad económica, "
                    "vulnerabilidad y renta.",
                )
                answer = "".join(answer)
                answer += (
                    "\n\nProveniencia de datos y variables:\n"
                    f"• Capas: {data_layers_text}\n"
                    f"• Herramientas: {tools_text}\n"
                    f"• Variables clave: {variables_text}\n\n"
                    "Para formación laboral, esto significa priorizar secciones con capacidad productiva real, necesidad de recualificación "
                    "y perfiles de ocupación que faciliten trayectorias hacia empleo estable."
                )
            else:
                answer = (
                    "No. En la respuesta anterior no se usó la capa de Inteligencia Socioeconómica con suficiente peso. "
                    f"Estaba apoyada principalmente en: {data_layers_text}.\n\n"
                    "Para una formación laboral debería incorporar explícitamente potencial productivo, ocupación y actividad económica, "
                    "empleo/desempleo, renta y población en edad activa. Con ese criterio, la recomendación podría cambiar."
                )
        elif any(token in text for token in ("variable", "variables", "datos", "de donde", "de dónde", "donde sale", "que datos", "qué datos", "herramientas")):
            answer = (
                "La recomendación anterior se basó en estas capas y herramientas:\n"
                f"• Capas: {data_layers_text}\n"
                f"• Herramientas: {tools_text}\n"
                f"• Variables observadas/proxy: {variables_text}\n"
                f"• Secciones recomendadas: {sections_text}\n"
                f"• Limitaciones: {limitations_text}"
            )
        else:
            answer = (
                "Sí, lo puedo explicar sobre la recomendación anterior. "
                f"El dominio detectado fue `{context.get('last_detected_domain')}`, el workflow fue `{context.get('last_workflow')}` "
                f"y las capas usadas fueron: {data_layers_text}."
            )

        return AnalystChatResponse(
            answer=answer,
            methodology="",
            confidence="high",
            display_mode="chat",
            data_used=context.get("last_data_used", []),
            data_layers_used=layers,
            tools_used=tools,
            variables_used=variables,
            limitations=limitations,
            follow_up_questions=[
                "¿Quieres que rehaga el ranking incorporando más peso socioeconómico?",
                "¿Quieres ver las variables por sección?",
                "¿Quieres separar necesidad laboral y potencial productivo?",
            ],
            warnings=[],
            conversation_id=conversation_id,
        )

    def _build_dialogue_response(
        self,
        decision: DialogueDecision,
        message: str,
        conversation_id: str,
    ) -> AnalystChatResponse:
        if decision.dialogue_action == "explain_capabilities":
            return self._build_conversational_response(message, conversation_id)

        if decision.dialogue_action == "continue_previous_analysis":
            pending = (decision.analysis_brief or {}).get("pending_clarification")
            if pending and pending.get("detected_context", {}).get("domain") == "housing":
                answer = (
                    "Perfecto. Si la prioridad es vivir con niños pequeños, no haría un ranking inmobiliario genérico. "
                    "Miraría entorno familiar, población infantil como proxy, edad media, crecimiento residencial, densidad, renta y servicios cercanos.\n\n"
                    "Sobre colegios: si la capa directa de centros educativos no está cargada, no la invento. Puedo aproximar zonas familiares con los indicadores demográficos y residenciales disponibles, y dejar explícita esa limitación.\n\n"
                    "Siguiente paso: dime si priorizamos cercanía a servicios educativos, tranquilidad residencial o precio de vivienda, y con eso cruzo las capas adecuadas."
                )
                return AnalystChatResponse(
                    answer=answer,
                    methodology="Continuacion consultiva del contexto de vivienda; no se ejecuta ranking hasta fijar criterio.",
                    confidence="medium",
                    display_mode="chat",
                    data_used=[],
                    data_layers_used=[],
                    tools_used=[],
                    variables_used=[],
                    limitations=["No se confirma capa directa de colegios en este turno; se propone trabajar con proxies si hace falta."],
                    follow_up_questions=[
                        "Prioriza cercanía a servicios educativos",
                        "Prioriza tranquilidad residencial",
                        "Prioriza precio de vivienda",
                    ],
                    warnings=[],
                    conversation_id=conversation_id,
                )
            return self._build_contextual_followup_response(message, conversation_id)

        answer = decision.clarification_question or (
            "Necesito una precisión antes de usar datos. ¿Qué objetivo quieres optimizar?"
        )
        return AnalystChatResponse(
            answer=answer,
            methodology=f"Consultative dialogue layer: action={decision.dialogue_action}; reason={decision.reason}",
            confidence="medium",
            display_mode="chat",
            data_used=[],
            data_layers_used=[],
            tools_used=[],
            variables_used=[],
            sections=[],
            tables=[],
            charts=[],
            strategic_recommendations=[],
            follow_up_questions=[],
            warnings=[],
            conversation_id=conversation_id,
        )

    def _remember_dialogue_turn(
        self,
        conversation_id: str,
        message: str,
        decision: DialogueDecision,
        response: AnalystChatResponse,
    ) -> None:
        previous = self._conversation_context.get(conversation_id, {})
        detected = decision.detected_context.model_dump()
        pending = decision.model_dump() if decision.dialogue_action == "ask_clarification" else previous.get("pending_clarification")
        if decision.dialogue_action == "continue_previous_analysis":
            pending = None
        self._conversation_context[conversation_id] = {
            **previous,
            "last_user_message": message,
            "last_domain": detected.get("domain") or previous.get("last_domain", ""),
            "last_user_goal": detected.get("user_goal") or previous.get("last_user_goal", ""),
            "last_detected_domain": detected.get("domain") or previous.get("last_detected_domain", ""),
            "last_detected_intent": detected.get("user_goal") or previous.get("last_detected_intent", ""),
            "last_workflow": "dialogue_manager",
            "last_tools_used": response.tools_used,
            "last_data_used": response.data_used,
            "last_data_layers_used": response.data_layers_used,
            "last_variables_used": response.variables_used,
            "last_answer_summary": response.answer[:600],
            "last_limitations": response.limitations,
            "pending_clarification": pending,
        }

    def _remember_turn(
        self,
        *,
        conversation_id: str,
        message: str,
        plan: PoliticalPlan,
        workflow_output: WorkflowOutput,
        response: AnalystChatResponse,
    ) -> None:
        rows = workflow_output.tool_result.rows
        self._conversation_context[conversation_id] = {
            "last_user_message": message,
            "last_domain": plan.domain,
            "last_user_goal": plan.goal,
            "last_detected_domain": plan.domain,
            "last_detected_intent": plan.goal,
            "last_workflow": workflow_output.tool_result.name,
            "last_tools_used": workflow_output.tool_names,
            "last_data_used": workflow_output.tool_result.data_used,
            "last_data_layers_used": response.data_layers_used,
            "last_variables_used": response.variables_used,
            "last_sections_recommended": [
                str(row.get("section_name") or row.get("section_id"))
                for row in rows[:5]
                if row.get("section_id") or row.get("section_name")
            ],
            "last_evidence_table": response.evidence_table,
            "last_answer_summary": response.answer[:600],
            "last_limitations": response.limitations,
            "pending_clarification": None,
        }

    async def _try_llm_synthesis(
        self,
        *,
        message: str,
        tool_result: AnalystToolResult,
        fallback_answer: str,
        fallback_methodology: str,
        conversation_id: str,
        plan: PoliticalPlan | None = None,
    ) -> dict[str, Any] | None:
        if self.settings.llm_provider.strip().lower() != "gemini" or not self.settings.gemini_api_key:
            return None
        try:
            provider = get_llm_provider("gemini", fallback_to_mock=False)
            synthesis = await provider.synthesize(
                LLMSynthesisRequest(
                    question=message,
                    system_prompt=POLITICAL_ANALYST_SYSTEM_PROMPT,
                    tool_result={
                        "summary": {"answer": fallback_answer},
                        "rows": _jsonable(tool_result.rows),
                        "methodology_plain": fallback_methodology,
                        "sources": tool_result.data_used,
                        "caveats": tool_result.warnings,
                        "plan": plan.model_dump() if plan else None,
                        "conversation_id": conversation_id,
                    },
                    conversation_context=AnalystConversationMemory(conversation_id=conversation_id).context(),
                    response_style="detailed",
                    locale="es-ES",
                )
            )
            grounding = _is_grounded_synthesis(synthesis.answer, tool_result)
            if not grounding.allowed:
                logger.info(
                    "Gemini political analyst synthesis discarded by grounding guard",
                    extra={
                        "tool": tool_result.name,
                        "row_count": len(tool_result.rows),
                        "reason": grounding.reason,
                        "violations": grounding.violations,
                    },
                )
                return None
            return {
                "answer": synthesis.answer,
                "methodology": synthesis.methodology,
                "warnings": _public_warnings(synthesis.caveats),
            }
        except (LLMProviderError, RuntimeError, asyncio.TimeoutError) as exc:
            logger.warning("Gemini political analyst synthesis failed; using deterministic answer", extra={"error": str(exc)})
            return None

    def _sections_from_rows(self, rows: list[dict[str, Any]]) -> list[AnalystSection]:
        sections: list[AnalystSection] = []
        for row in rows:
            section_id = str(row.get("section_id") or "")
            if not section_id:
                continue
            tags = self.classifier.classify(row)
            score = _float(row.get("opportunity_score"))
            sections.append(
                AnalystSection(
                    section_id=section_id,
                    name=str(row.get("section_name") or section_id),
                    score=score,
                    tags=tags,
                    metrics={
                        key: value
                        for key, value in row.items()
                        if key not in {"section_id", "section_name"} and value is not None
                    },
                    rationale=self._section_rationale(row, tags),
                )
            )
        return sections

    def _table_from_rows(self, intent: str, rows: list[dict[str, Any]]) -> AnalystTable:
        if intent == "dhondt":
            return AnalystTable(
                title="Cocientes D'Hondt ganadores",
                columns=["Partido", "Divisor", "Cociente"],
                rows=[
                    [str(row.get("party", "")), str(row.get("divisor", "")), str(row.get("quotient", ""))]
                    for row in rows[:25]
                ],
            )
        if intent == "population_ranking":
            return AnalystTable(
                title="Secciones por poblacion",
                columns=["Seccion", "Poblacion", "Densidad"],
                rows=[
                    [
                        str(row.get("section_name") or row.get("section_id") or ""),
                        str(row.get("population_total") or ""),
                        _fmt(row.get("population_density")),
                    ]
                    for row in rows
                ],
            )
        columns = [
            "Seccion",
            "Poblacion",
            "Ganador",
            "Voto ganador",
            "Segundo",
            "Margen",
            "Voto objetivo",
            "Abstencion",
            "Crec. poblacion",
            "Edad media",
            "Renta",
            "Score",
            "Etiqueta",
            "Motivo",
        ]
        return AnalystTable(
            title="Evidencia territorial",
            columns=columns,
            rows=[
                [
                    str(row.get("section_name") or row.get("section_id") or ""),
                    str(row.get("population_total") or ""),
                    str(row.get("winning_party") or row.get("party") or ""),
                    _pct(row.get("winning_party_pct")),
                    _pct(row.get("runner_up_pct")),
                    _pct(row.get("victory_margin_pct")),
                    _pct(row.get("target_party_vote_pct") or row.get("vote_pct")),
                    _pct(row.get("abstention_rate_pct")),
                    _pct(row.get("population_growth_pct")),
                    _fmt(row.get("avg_age") or row.get("average_age")),
                    _euro(row.get("income") or row.get("individual_income")),
                    _fmt(row.get("opportunity_score")),
                    str(row.get("strategic_label") or ""),
                    str(row.get("reason") or ""),
                ]
                for row in rows
            ],
        )

    def _chart_from_rows(self, intent: str, rows: list[dict[str, Any]]) -> AnalystChart:
        metric = (
            "opportunity_score"
            if intent in {"candidate_visit", "opportunity", "campaign_plan", "candidate_visit_plan", "party_growth_opportunity"}
            else "population_total"
            if intent in {"population_ranking", "population_max_section"}
            else "elderly_population"
            if intent == "elderly_population_max_section"
            else "population_change"
            if intent in {"population_change_sections", "population_change_between_years"}
            else "turnout_change_pct"
            if intent == "electoral_change_between_years"
            else "individual_income_change"
            if intent == "income_change_between_years"
            else "average_age"
            if intent == "youngest_section"
            else "abstention_rate_pct"
        )
        return AnalystChart(
            kind="bar",
            title="Ranking territorial",
            data=[
                {
                    "section": row.get("section_name") or row.get("section_id"),
                    "value": _float(row.get(metric)) or 0,
                    "metric": metric,
                }
                for row in rows[:8]
                if row.get("section_id") or row.get("section_name")
            ],
        )

    def _recommendations(self, intent: str, sections: list[AnalystSection]) -> list[StrategicRecommendation]:
        if intent not in {"candidate_visit", "opportunity", "abstention", "campaign_plan", "candidate_visit_plan", "abstention_analysis", "party_growth_opportunity"}:
            return []
        recommendations: list[StrategicRecommendation] = []
        for section in sections[:3]:
            actions = ["Visita presencial con mensaje local", "Segmentar incidencias de abstencion", "Contrastar lectura con Dashboard antes de invertir presupuesto"]
            if "Digital Campaign Priority" in section.tags:
                actions.insert(1, "Refuerzo de creatividades digitales geolocalizadas")
            recommendations.append(
                StrategicRecommendation(
                    priority="high" if section.score is not None and section.score >= 70 else "medium",
                    section_id=section.section_id,
                    title=f"Priorizar {section.name}",
                    rationale=section.rationale or "Combina oportunidad electoral y tamano territorial suficiente.",
                    actions=actions,
                )
            )
        return recommendations

    def _deterministic_answer(
        self,
        intent: str,
        tool_result: AnalystToolResult,
        sections: list[AnalystSection],
        plan: PoliticalPlan | None = None,
    ) -> str:
        if not tool_result.rows:
            return (
                "Puedo darte un marco politico, pero no tengo filas internas suficientes para priorizar secciones "
                "sin inventar evidencia territorial."
            )
        if intent == "dhondt":
            return "He calculado los cocientes D'Hondt con votos observados municipales. La tabla muestra los 25 cocientes que entran en el reparto."
        first = sections[0] if sections else None
        if intent == "abstention" and first:
            abstention = _pct(first.metrics.get("abstention_rate_pct"))
            return f"La abstencion mas alta detectada esta en {first.name}, con {abstention}. Es una zona prioritaria para movilizacion, no una prediccion."
        if intent == "population_ranking" and first:
            population = first.metrics.get("population_total")
            return f"La seccion electoral mas poblada detectada es {first.name}, con {population} habitantes en la capa de poblacion usada."
        if intent == "population_max_section":
            row = tool_result.rows[0]
            return self._population_max_answer(tool_result)
        if intent == "elderly_population_max_section":
            return self._elderly_population_max_answer(tool_result)
        if intent == "population_change_between_years":
            start_year = plan.start_year if plan and plan.start_year else 2019
            end_year = plan.end_year if plan and plan.end_year else 2023
            return self._population_change_answer(tool_result, start_year, end_year)
        if intent == "electoral_change_between_years":
            start_year = plan.start_year if plan and plan.start_year else 2019
            end_year = plan.end_year if plan and plan.end_year else 2023
            return self._electoral_change_answer(tool_result, start_year, end_year)
        if intent == "income_change_between_years":
            start_year = plan.start_year if plan and plan.start_year else 2019
            end_year = plan.end_year if plan and plan.end_year else 2023
            return self._income_change_answer(tool_result, start_year, end_year)
        if intent == "candidate_visit" and first:
            return f"El primer punto de visita recomendado es {first.name}. La prioridad sale de combinar abstencion, competitividad y tamano seccional con datos observados."
        if intent == "campaign_plan" and first:
            return _campaign_plan_answer(first, sections, plan)
        if intent == "candidate_visit_plan" and first:
            return _candidate_visit_answer(first, sections)
        if intent == "abstention_analysis" and first:
            return _abstention_answer(first, sections)
        if intent == "party_growth_opportunity" and first:
            party = plan.target_party if plan else "el partido objetivo"
            return _growth_answer(first, sections, party)
        if intent == "opportunity" and first:
            return f"La mejor oportunidad territorial inicial aparece en {first.name}. El ranking no es forecast: ordena secciones por una regla auditable de oportunidad."
        if first:
            return f"El resultado principal es {first.name}. Revisa la tabla para ver la evidencia territorial usada."
        return "He obtenido resultados estructurados con herramientas internas aprobadas."

    def _section_rationale(self, row: dict[str, Any], tags: list[str]) -> str:
        parts = []
        if row.get("opportunity_score") is not None:
            parts.append(f"score {_fmt(row.get('opportunity_score'))}")
        if row.get("abstention_rate_pct") is not None:
            parts.append(f"abstencion {_pct(row.get('abstention_rate_pct'))}")
        if row.get("distance_to_winner_pct") is not None:
            parts.append(f"distancia al ganador {_pct(row.get('distance_to_winner_pct'))}")
        if tags:
            parts.append("tags: " + ", ".join(tags[:3]))
        return "; ".join(parts) if parts else "Perfil construido con datos territoriales observados."

    def _detect_intent(self, message: str) -> str:
        text = _normalize(message)
        if re.search(r"d\s*['’]?\s*hondt|concejal|escano|reparto", text):
            return "dhondt"
        if re.search(r"abstencion|participacion|moviliza", text):
            return "abstention"
        if re.search(r"visitar|candidato|campana|recursos|roi|prioridad", text):
            return "candidate_visit"
        if re.search(r"mas poblada|más poblada|mayor poblacion|mayor población|mas poblacion|más población|mas habitantes|más habitantes|most populated|largest population", text):
            return "population_ranking"
        if re.search(r"crec|growth|poblacion nueva|residencial", text):
            return "population_growth"
        if re.search(r"joven|edad|envejec|mayores", text):
            return "age"
        if re.search(r"renta|income|ingreso", text):
            return "income"
        if re.search(r"catastro|suelo|constru|urbano|built", text):
            return "land_built"
        if re.search(r"seccion\s+\d+|29\d{8}|perfil", text):
            return "section_profile"
        if re.search(r"oportunidad|puede crecer|grow|swing|persuasion|persuasion", text):
            return "opportunity"
        return "general_territorial_advice"

    def _legacy_intent(self, goal: str, message: str) -> str:
        mapping = {
            "candidate_visit_plan": "candidate_visit",
            "abstention_analysis": "abstention",
            "party_growth_opportunity": "opportunity",
            "electoral_diagnosis": self._detect_intent(message),
            "section_profile": "section_profile",
            "comparison": "section_profile",
            "general_political_advice": self._detect_intent(message),
        }
        return mapping.get(goal, self._detect_intent(message))

    def _follow_ups(self, intent: str) -> list[str]:
        common = [
            "¿Qué secciones debería visitar primero el candidato?",
            "¿Dónde es más alta la abstención?",
        ]
        if intent == "campaign_plan":
            return [
                "Adapta el plan para el PP",
                "¿Qué mensaje usarías en las secciones prioritarias?",
                "¿Cómo organizarías la agenda semanal del candidato?",
                *common,
            ]
        if intent == "candidate_visit_plan":
            return ["¿Qué mensaje local llevaría a cada visita?", "¿Dónde harías puerta a puerta?", *common]
        if intent == "party_growth_opportunity":
            return ["Distingue movilización y persuasión por sección", "¿Qué zonas visitaría primero el candidato?", *common]
        if intent == "abstention_analysis":
            return ["¿Qué acciones de movilización recomiendas?", "¿Qué secciones tienen más jóvenes y más abstención?", *common]
        if intent == "opportunity":
            return ["¿Qué mensaje debería usar en esas secciones?", "¿Qué zonas combinan renta y oportunidad electoral?", *common]
        if intent == "abstention":
            return ["¿Dónde hay oportunidad de movilización?", "¿Qué secciones tienen más jóvenes y más abstención?", *common]
        if intent in {
            "population_max_section",
            "elderly_population_max_section",
            "population_change_between_years",
            "electoral_change_between_years",
            "income_change_between_years",
        }:
            return [
                "¿Quieres ver el ranking completo de secciones?",
                "¿Quieres comparar esta sección con la media municipal?",
                "¿Quieres cruzarlo con renta, edad o voto?",
            ]
        return common

    def _audit(
        self,
        message: str,
        municipality_id: str,
        intent: str,
        tool_result: AnalystToolResult | None,
        response: AnalystChatResponse,
        error: str | None = None,
        tool_names: list[str] | None = None,
    ) -> str | None:
        if not hasattr(self.session, "execute"):
            return None
        try:
            return self.audit_repository.audit(
                question=message,
                municipality_id=municipality_id,
                intent=f"political_analyst:{intent}",
                tools=tool_names or ([tool_result.name] if tool_result else []),
                datasets=response.data_used,
                answer=response.answer,
                confidence_level=response.confidence,
                methodological_notes=[response.methodology],
                error=error,
            )
        except Exception:
            logger.exception("Political analyst audit failed")
            if hasattr(self.session, "rollback"):
                self.session.rollback()
            return None


def get_political_analyst_agent(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> PoliticalAnalystAgent:
    return PoliticalAnalystAgent(session=session, settings=settings)


def _sanitize(value: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value).strip()


def _normalize(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(char) != "Mn"
    )


def _extract_party(value: str) -> str | None:
    text = _normalize(value)
    for party, aliases in {
        "PP": ["pp", "partido popular"],
        "PSOE": ["psoe", "partido socialista"],
        "VOX": ["vox"],
        "CS": ["cs", "ciudadanos"],
    }.items():
        if any(re.search(rf"(^|[^a-z0-9]){re.escape(alias)}([^a-z0-9]|$)", text) for alias in aliases):
            return party
    return None


def _extract_section_id(value: str) -> str | None:
    match = re.search(r"\b29\d{8}\b", value)
    return match.group(0) if match else None


def _is_aging_question(value: str) -> bool:
    return bool(re.search(r"envejec|mayores|vieja|older|aging", _normalize(value)))


def _float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _data_layers(data_used: list[str]) -> list[str]:
    labels = {
        "marts.v_population_layer": "Population",
        "marts.v_mapa_age_structure_2023": "Age Structure",
        "marts.v_income_level_layer": "Income Level",
        "marts.socioeconomic_intelligence_signals": "Socioeconomic Intelligence",
        "marts.v_land_built_environment": "Urban Intelligence",
        "marts.territorial_intelligence_section_2023": "Urban Intelligence",
        "marts.mv_electoral_behavior": "Electoral Behavior",
        "core.resultados_seccion": "Electoral Behavior",
    }
    output: list[str] = []
    for dataset in data_used:
        label = labels.get(dataset)
        if label and label not in output:
            output.append(label)
    return output


def _variables_used(rows: list[dict[str, Any]]) -> list[str]:
    ignored = {"section_id", "section_name", "priority", "data_support", "reason", "recommended_action", "recommended_channel"}
    output: list[str] = []
    for row in rows[:8]:
        for key, value in row.items():
            if key in ignored or value is None or value == "":
                continue
            if key not in output:
                output.append(str(key))
    return output[:30]


def _fmt(value: Any) -> str:
    number = _float(value)
    return "" if number is None else f"{number:.1f}"


def _fmt_int(value: Any) -> str:
    number = _float(value)
    return "" if number is None else f"{number:,.0f}".replace(",", ".")


def _format_cell(value: Any, *, key: str) -> str:
    if value is None:
        return ""
    if key.endswith("_pct") or key in {"over_65_pct", "under_30_pct"}:
        return _pct(value)
    if key in {
        "population_total",
        "elderly_population",
        "population_start",
        "population_end",
        "population_change",
        "individual_income_start",
        "individual_income_end",
        "individual_income_change",
    }:
        return _fmt_int(value)
    if key in {"population_density"}:
        return _fmt(value)
    return str(value)


def _pct(value: Any) -> str:
    number = _float(value)
    return "" if number is None else f"{number:.1f}%"


def _euro(value: Any) -> str:
    number = _float(value)
    return "" if number is None else f"{number:,.0f} EUR".replace(",", ".")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _campaign_plan_answer(first: AnalystSection, sections: list[AnalystSection], plan: PoliticalPlan | None) -> str:
    party_note = (
        f"Lo aterrizo para {plan.target_party}."
        if plan and plan.target_party
        else "Como no has fijado partido, lo planteo como marco neutral de campana municipal. Para afinar el analisis puedo adaptar la estrategia a un partido, presupuesto o candidato concreto."
    )
    names = ", ".join(section.name for section in sections[:4])
    return (
        f"Si tuviera que organizar la campana en Mijas, empezaria por dividir el municipio en tres frentes: "
        f"movilizacion, persuasion y presencia territorial. {party_note}\n\n"
        f"Diagnostico politico\n"
        f"• La primera prioridad territorial es {first.name}. El ranking combina datos observados de voto, abstencion, margen competitivo, poblacion, edad y renta.\n"
        f"• Las secciones que usaria como primer mapa operativo son: {names}.\n"
        f"• Donde la abstencion pesa mas, la accion debe ser movilizacion; donde el margen es estrecho, persuasion; donde ya hay fuerza propia, retencion y presencia.\n\n"
        f"Plan de campana\n"
        f"• Fase 1: escucha territorial y validacion local en las secciones prioritarias.\n"
        f"• Fase 2: agenda del candidato con visitas de alto contacto, reuniones vecinales y puerta a puerta.\n"
        f"• Fase 3: mensajes por segmento: servicios publicos y seguridad en zonas de movilizacion; gestion y confianza en zonas de persuasion; orgullo de barrio y continuidad donde haya retencion.\n"
        f"• Fase 4: cierre con recordatorio de voto, interventores y seguimiento de abstencion.\n\n"
        f"Limitacion\n"
        f"• Esto no es una encuesta ni un forecast: es una priorizacion operativa sobre datos internos disponibles."
    )


def _candidate_visit_answer(first: AnalystSection, sections: list[AnalystSection]) -> str:
    names = ", ".join(section.name for section in sections[:5])
    return (
        f"Empezaria la agenda del candidato por {first.name}. Despues ordenaria las visitas asi: {names}.\n\n"
        "La logica es politica, no solo numerica: combinar zonas con abstencion movilizable, margen competitivo y suficiente tamano territorial. "
        "En cada visita conviene llevar un mensaje local, escuchar demandas concretas y cerrar con una accion medible: captacion de apoderados, lista de contactos o convocatoria vecinal."
    )


def _abstention_answer(first: AnalystSection, sections: list[AnalystSection]) -> str:
    names = ", ".join(section.name for section in sections[:5])
    abstention = _pct(first.metrics.get("abstention_rate_pct"))
    return (
        f"La abstencion mas alta del ranking aparece en {first.name}, con {abstention}. "
        f"Las primeras zonas de movilizacion serian: {names}.\n\n"
        "Recomendacion: tratar estas secciones como operacion de participacion, no como persuasion pura. "
        "El trabajo debe centrarse en contacto directo, recordatorio de voto, problemas cotidianos del barrio y redes locales que reduzcan friccion el dia electoral."
    )


def _growth_answer(first: AnalystSection, sections: list[AnalystSection], party: str | None) -> str:
    label = party or "el partido objetivo"
    names = ", ".join(section.name for section in sections[:5])
    return (
        f"Para {label}, la primera oportunidad territorial aparece en {first.name}. "
        f"El bloque inicial de crecimiento seria: {names}.\n\n"
        "Distingo cuatro tipos de crecimiento: movilizacion donde hay abstencion alta, persuasion donde el margen es estrecho, "
        "retencion donde ya existe fuerza propia y expansion donde el partido necesita presencia sostenida. "
        "La tabla de evidencia muestra que tipo de accion encaja mejor en cada seccion."
    )


def _public_warnings(warnings: list[str]) -> list[str]:
    blocked = [
        "fallback",
        "deterministic",
        "gemini synthesis",
        "debug",
        "tool failure",
        "no section-level evidence table",
    ]
    cleaned: list[str] = []
    for warning in warnings:
        if not warning:
            continue
        normalized = _normalize(warning)
        if any(marker in normalized for marker in blocked):
            continue
        cleaned.append(warning)
    return list(dict.fromkeys(cleaned))


def _is_grounded_synthesis(answer: str, tool_result: AnalystToolResult) -> GroundingDecision:
    normalized = _normalize(answer)
    violations: list[str] = []
    unsupported_markers = [
        "encuesta interna",
        "sondeo",
        "tracking propio",
        "modelo predictivo entrenado",
        "dato externo",
        "dataset externo",
    ]
    if any(marker in normalized for marker in unsupported_markers):
        violations.append("unsupported_dataset_or_poll_claim")

    if tool_result.rows:
        allowed_section_ids = {str(row.get("section_id")) for row in tool_result.rows if row.get("section_id")}
        mentioned_section_ids = set(re.findall(r"\b29\d{8}\b", answer))
        invented_ids = mentioned_section_ids - allowed_section_ids
        if invented_ids:
            violations.append(f"invented_section_ids:{','.join(sorted(invented_ids))}")
        allowed_names = {_normalize(str(row.get("section_name") or "")) for row in tool_result.rows if row.get("section_name")}
        known_mijas_section_pattern = re.findall(r"secci[oó]n\s+\d+", normalized)
        for section_name in known_mijas_section_pattern:
            if not any(section_name in name for name in allowed_names) and not any(section_name in _normalize(str(row.get("section_id") or "")) for row in tool_result.rows):
                violations.append(f"unanchored_section_name:{section_name}")
                break
    if violations:
        return GroundingDecision(
            allowed=False,
            reason="La sintesis contiene afirmaciones no ancladas en las filas disponibles.",
            violations=violations,
        )
    return GroundingDecision(
        allowed=True,
        reason="La sintesis contiene juicio politico permitido y esta anclada en la evidencia disponible.",
        violations=[],
    )
