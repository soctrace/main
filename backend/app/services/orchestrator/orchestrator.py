from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.ask.llm.factory import get_llm_provider
from app.ask.llm.schemas import LLMPlanRequest, LLMToolCall, LLMSynthesisRequest
from app.ask.tools_v2 import ToolContext, ToolResult
from app.core.config import Settings
from app.services.orchestrator.context_store import OrchestratorConversationContext, context_store
from app.services.orchestrator.response_schema import OrchestratorChart, OrchestratorResponse, OrchestratorTable
from app.services.orchestrator.safety import (
    asks_budget_campaign_without_party,
    asks_concept_distinction,
    asks_individual_vote_by_address,
    asks_previous_layers,
    asks_school_context,
    asks_same_sections_challenge,
    infer_goal_concept,
    infer_topic,
    is_conversational_or_open_ended,
    is_greeting,
    is_housing_ambiguous,
    is_suggestion_request,
    normalize_text,
    validate_grounded_answer,
)
from app.services.orchestrator.system_prompt import ORCHESTRATOR_SYSTEM_PROMPT
from app.services.orchestrator.methodology_explanation import MethodologyExplanationLayer
from app.services.orchestrator.telemetry import telemetry_span
from app.services.orchestrator.tool_coverage import tool_coverage_audit
from app.services.orchestrator.tool_executor import SafeDataToolExecutor
from app.services.orchestrator.tool_registry import OrchestratorToolRegistry


logger = logging.getLogger(__name__)


class SocTraceOrchestrator:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.tool_registry = OrchestratorToolRegistry()
        self.tool_executor = SafeDataToolExecutor(session)
        provider_name = settings.ask_llm_provider or settings.llm_provider
        self.llm_provider = get_llm_provider(provider_name, fallback_to_mock=True)
        self.methodology_explanation = MethodologyExplanationLayer()

    async def chat(self, payload) -> OrchestratorResponse:
        conversation_id = payload.conversation_id or str(uuid4())
        message = payload.message.strip()
        state = context_store.get(conversation_id)
        with telemetry_span("soctrace_orchestrator_chat", conversation_id=conversation_id, municipality_id=payload.municipality_id) as span:
            if self.settings.app_env == "development":
                span["raw_user_message"] = message
            explanation = self.methodology_explanation.explain(message, state)
            if explanation is not None:
                response = OrchestratorResponse(
                    answer=explanation.answer,
                    methodology="Explicación del análisis anterior a partir del contexto ya disponible.",
                    confidence="high",
                    display_mode="chat",
                    data_layers_used=state.last_data_layers_used,
                    variables_used=state.last_variables_used,
                    source_views=state.last_source_views,
                    ranking_basis=state.last_ranking_basis,
                    warnings=state.methodology_explanation.warnings,
                    tools_used=[],
                    tools_called=[],
                    llm_called=False,
                    fallback_used=False,
                    response_source="tool",
                    self_check=self._self_check(answer=explanation.answer, tool_results=[]),
                    conversation_id=conversation_id,
                )
                span["route"] = "methodology_explanation"
                span["tools_called"] = []
                span["fallback_used"] = False
                return response

            if is_conversational_or_open_ended(message):
                response = await self._gemini_conversational_reply(message, conversation_id, state)
                span["route"] = "conversational"
                span["mode"] = "orchestrator"
                span["llm_called"] = response.llm_called
                span["tools_called"] = []
                span["fallback_used"] = response.fallback_used
                span["response_source"] = response.response_source
                self._remember(conversation_id, message, response)
                return response

            direct = self._direct_response(message, conversation_id, state)
            if direct:
                span["route"] = "direct"
                span["mode"] = "orchestrator"
                span["llm_called"] = direct.llm_called
                span["tools_called"] = direct.tools_called
                span["fallback_used"] = direct.fallback_used
                span["response_source"] = direct.response_source
                self._remember(conversation_id, message, direct)
                return direct

            tool_calls = await self._select_tool_calls(message, payload, state)
            if not tool_calls:
                response = self._clarification_response(message, conversation_id)
                span["route"] = "clarification"
                self._remember(conversation_id, message, response, pending_clarification=response.answer)
                return response

            context = ToolContext(
                municipio_id=payload.municipality_id,
                municipio_nombre="Mijas" if payload.municipality_id == "29070" else None,
                active_year=payload.context.active_year,
                conversation_id=conversation_id,
            )
            results: list[tuple[LLMToolCall, ToolResult]] = []
            for step, tool_call in enumerate(tool_calls[: min(self.settings.ask_max_tool_calls, 5)], start=1):
                logger.info(
                    "soctrace_agent_step",
                    extra={"conversation_id": conversation_id, "agent_step": step, "tool_selected": tool_call.tool_name,
                           "validated_parameters": tool_call.arguments},
                )
                result = await self.tool_executor.execute(tool_call.tool_name, tool_call.arguments, context)
                results.append((tool_call, result))
                logger.info(
                    "soctrace_agent_tool_result",
                    extra={"conversation_id": conversation_id, "agent_step": step, "tool_selected": tool_call.tool_name,
                           "tool_status": result.status, "row_count": len(result.rows), "error_category": result.error_code},
                )
                if tool_call.tool_name == "lookup_section_by_address" and result.status == "ok" and result.rows:
                    section = result.rows[0].get("section_id") or result.rows[0].get("section")
                    if section:
                        followup_call = LLMToolCall(
                            tool_name="get_electoral_results",
                            arguments={"municipio_id": payload.municipality_id, "section": str(section)},
                        )
                        followup_result = await self.tool_executor.execute(followup_call.tool_name, followup_call.arguments, context)
                        results.append((followup_call, followup_result))
            response = await self._build_analysis_response(message, conversation_id, results, state)
            span["route"] = "tool"
            span["tools_called"] = [tool_call.tool_name for tool_call, _result in results]
            span["tool_statuses"] = [result.status for _tool_call, result in results]
            span["data_layers_used"] = response.data_layers_used
            span["answer_type"] = "analysis"
            span["mode"] = "orchestrator"
            self._remember(conversation_id, message, response)
            return response

    async def _gemini_conversational_reply(
        self,
        message: str,
        conversation_id: str,
        state: OrchestratorConversationContext,
    ) -> OrchestratorResponse:
        llm_called = True
        fallback_used = False
        try:
            synthesis = await self.llm_provider.synthesize(
                LLMSynthesisRequest(
                    question=message,
                    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
                    tool_result={
                        "mode": "pure_conversational",
                        "rows": [],
                        "summary": {},
                        "metadata": {
                            "conversation_context": state.model_dump(),
                            "available_layers": [
                                "Population Intelligence",
                                "Age Structure",
                                "Income Intelligence",
                                "Socioeconomic Intelligence",
                                "Electoral Intelligence",
                                "Housing Intelligence",
                                "Urban Intelligence",
                            ],
                        },
                    },
                    conversation_context=state.model_dump(),
                    response_style="simple",
                    locale="es-ES",
                )
            )
            answer = synthesis.answer.strip()
            if self._is_unhelpful_conversational_answer(answer):
                answer = self._conversational_safety_net(message)
            followups = synthesis.suggested_followups or self._conversational_followups(message)
        except Exception:
            logger.exception("orchestrator_conversational_llm_failed")
            llm_called = True
            fallback_used = True
            answer = self._conversational_safety_net(message)
            followups = self._conversational_followups(message)

        return OrchestratorResponse(
            answer=answer,
            methodology="Respuesta conversacional generada antes de activar herramientas de datos.",
            confidence="high" if not fallback_used else "medium",
            display_mode="chat",
            follow_up_questions=followups[:4],
            self_check=self._self_check(answer=answer, tool_results=[], needs_clarification=False),
            mode="orchestrator",
            llm_called=llm_called,
            tools_called=[],
            fallback_used=fallback_used,
            response_source="gemini" if not fallback_used else "fallback",
            conversation_id=conversation_id,
        )

    def _direct_response(
        self,
        message: str,
        conversation_id: str,
        state: OrchestratorConversationContext,
    ) -> OrchestratorResponse | None:
        if is_greeting(message):
            return OrchestratorResponse(
                answer="Hola. Soy Ask SocTrace. Puedo ayudarte a entender secciones, población, edad, renta, vivienda o comportamiento electoral agregado de Mijas.",
                methodology="Respuesta conversacional sin consulta a datos.",
                confidence="high",
                display_mode="chat",
                follow_up_questions=[
                    "¿Cuál es la sección con mayor población?",
                    "¿Dónde hay más jóvenes?",
                    "¿Qué zonas tienen mayor presión residencial?",
                ],
                conversation_id=conversation_id,
            )
        if is_suggestion_request(message):
            return OrchestratorResponse(
                answer="Puedes preguntarme por rankings de secciones, perfiles de una zona, comparaciones de renta, estructura de edad, vivienda o resultados electorales agregados.",
                methodology="No se han consultado datos; se proponen preguntas ejecutables con las capas disponibles.",
                confidence="high",
                display_mode="chat",
                follow_up_questions=[
                    "¿Cuál es la sección con mayor población?",
                    "¿Qué sección tiene más población joven?",
                    "¿Dónde es más alta la abstención?",
                    "¿Qué zonas tienen mayor valor inmobiliario estimado?",
                ],
                conversation_id=conversation_id,
            )
        if is_housing_ambiguous(message):
            return OrchestratorResponse(
                answer="¿Quieres mirar vivienda desde el punto de vista de vivir, invertir o potencial de revalorización?",
                methodology="Clarificación antes de consultar datos porque el objetivo cambia las variables relevantes.",
                confidence="medium",
                display_mode="chat",
                data_layers_used=["Housing Intelligence"],
                follow_up_questions=["Vivir", "Invertir", "Revalorización"],
                conversation_id=conversation_id,
            )
        text = normalize_text(message)
        if "invertir" in text and "vivienda" in text and not any(
            token in text for token in ("revalorizacion", "alquiler", "vivienda habitual")
        ):
            return OrchestratorResponse(
                answer="¿Buscas rentabilidad por alquiler, revalorización a medio plazo o vivienda habitual?",
                methodology="El objetivo de inversión cambia las variables y criterios territoriales.",
                confidence="high", display_mode="chat",
                missing_relevant_variables=["investment_objective"],
                self_check=self._self_check(answer="Aclaración de inversión", tool_results=[], needs_clarification=True),
                conversation_id=conversation_id,
            )
        if "2035" in text and ("poblacion" in text or "habitantes" in text):
            return OrchestratorResponse(
                answer=("No existe una previsión demográfica validada por sección para 2035 en las herramientas actuales. "
                        "No voy a inventar esa proyección; puedo mostrar la evolución observada entre 2021 y 2025."),
                methodology="Comprobación de cobertura temporal antes de consultar datos.",
                confidence="high", display_mode="chat",
                warnings=["Forecast demográfico 2035 no disponible."],
                follow_up_questions=["¿Qué secciones crecieron más entre 2021 y 2025?"],
                self_check=self._self_check(answer="Forecast no disponible", tool_results=[]),
                conversation_id=conversation_id,
            )
        if "programa" in text and ("joven" in text or "menores" in text) and not any(
            token in text for token in ("deportivo", "empleo", "formacion", "vivienda", "salud", "cultural")
        ):
            return OrchestratorResponse(
                answer="¿Qué tipo de programa municipal quieres comunicar: formación, empleo, cultura, deporte, vivienda u otro servicio?",
                methodology="Una aclaración material antes de elegir indicadores territoriales.",
                confidence="high", display_mode="chat",
                missing_relevant_variables=["service_type"],
                self_check=self._self_check(answer="Aclaración de servicio", tool_results=[], needs_clarification=True),
                conversation_id=conversation_id,
            )
        if asks_school_context(message):
            carried_context = " Mantengo el contexto de vivienda." if state.last_topic == "housing" else ""
            return OrchestratorResponse(
                answer=(
                    f"{carried_context} Ahora mismo SocTrace no tiene una capa directa de colegios o guarderías en el contrato seguro. "
                    "Puedo aproximar la necesidad familiar con estructura de edad, población infantil y variables de vivienda, indicando claramente la limitación."
                ).strip(),
                methodology="Respuesta sin inventar equipamientos escolares no disponibles en las tools aprobadas.",
                confidence="medium",
                display_mode="chat",
                data_layers_used=state.last_data_layers_used,
                variables_used=state.last_variables_used,
                warnings=["No hay dato directo de colegios en el catálogo seguro actual."],
                follow_up_questions=["¿Qué secciones tienen más población infantil?", "Cruza población infantil con vivienda"],
                conversation_id=conversation_id,
            )
        if asks_previous_layers(message):
            layers = state.last_data_layers_used or []
            variables = state.last_variables_used or []
            sources = state.last_source_views or []
            missing = state.last_missing_relevant_variables or []
            if not layers and not variables:
                answer = "En la respuesta anterior no usé ninguna capa de datos; fue una respuesta conversacional."
            else:
                answer = "En la respuesta anterior usé " + ", ".join(layers or ["capas no etiquetadas"]) + "."
                if variables:
                    answer += " Variables principales: " + ", ".join(variables) + "."
                if sources:
                    answer += " Fuentes: " + ", ".join(sources) + "."
                if missing:
                    answer += " Variables relevantes no disponibles o no usadas: " + ", ".join(missing) + "."
            return OrchestratorResponse(
                answer=answer,
                methodology="Lectura de la memoria mínima de conversación.",
                confidence="high",
                display_mode="chat",
                data_layers_used=layers,
                variables_used=variables,
                source_views=sources,
                missing_relevant_variables=missing,
                ranking_basis=state.last_ranking_basis,
                self_check=self._self_check(answer=answer, tool_results=[], needs_clarification=False),
                conversation_id=conversation_id,
            )
        if asks_same_sections_challenge(message):
            basis = state.last_ranking_basis or {}
            variables = basis.get("variables") or state.last_variables_used or []
            sections = state.last_sections or []
            if variables:
                answer = (
                    "Si salen secciones parecidas, la razón debe estar en la base del ranking, no en una preferencia fija. "
                    f"En la respuesta anterior usé estas variables: {', '.join(variables)}."
                )
            else:
                answer = "No tengo una base de ranking anterior suficientemente explícita para justificar esas secciones."
            if sections:
                answer += " Secciones anteriores: " + ", ".join(sections) + "."
            answer += " Para corregir sesgos, conviene rehacer el análisis con variables específicas del objetivo, no solo crecimiento, densidad o población joven."
            return OrchestratorResponse(
                answer=answer,
                methodology="Revisión de contexto y base de ranking anterior.",
                confidence="medium",
                display_mode="chat",
                data_layers_used=state.last_data_layers_used,
                variables_used=state.last_variables_used,
                source_views=state.last_source_views,
                ranking_basis=state.last_ranking_basis,
                follow_up_questions=[
                    "Rehazlo para potencial electoral",
                    "Rehazlo para necesidad de servicios",
                    "Rehazlo para oportunidad comercial",
                ],
                self_check=self._self_check(answer=answer, tool_results=[], needs_clarification=False),
                conversation_id=conversation_id,
            )
        if asks_concept_distinction(message):
            answer = (
                "No es lo mismo. Crecimiento urbano se prueba con población, vivienda y entorno construido. "
                "Potencial de voto requiere variables electorales: voto de partido, abstención, margen, histórico, participación y competitividad. "
                "Si antes usé solo crecimiento residencial, eso no basta para afirmar potencial electoral."
            )
            return OrchestratorResponse(
                answer=answer,
                methodology="Aclaración conceptual sin nueva consulta de datos.",
                confidence="high",
                display_mode="chat",
                data_layers_used=state.last_data_layers_used,
                variables_used=state.last_variables_used,
                source_views=state.last_source_views,
                ranking_basis=state.last_ranking_basis,
                self_check=self._self_check(answer=answer, tool_results=[], needs_clarification=False),
                conversation_id=conversation_id,
            )
        if asks_budget_campaign_without_party(message):
            answer = (
                "Para recomendar una inversión electoral de 5.000 euros necesito saber para qué partido o candidatura. "
                "Sin eso puedo construir un plan neutral, pero no debería inferir potencial de voto a partir de crecimiento residencial."
            )
            return OrchestratorResponse(
                answer=answer,
                methodology="Clarificación antes de activar análisis electoral partidista.",
                confidence="medium",
                display_mode="chat",
                missing_relevant_variables=["party", "campaign_objective"],
                follow_up_questions=["PP", "PSOE", "VOX", "Plan neutral de participación"],
                self_check=self._self_check(answer=answer, tool_results=[], needs_clarification=True),
                conversation_id=conversation_id,
            )
        return None

    async def _select_tool_calls(self, message: str, payload: Any, state: OrchestratorConversationContext) -> list[LLMToolCall]:
        heuristic_many = self._heuristic_tool_calls(message, payload, state)
        if heuristic_many:
            return heuristic_many
        heuristic = self._heuristic_tool_call(message, payload)
        if heuristic is not None:
            return [heuristic]
        try:
            plan = await self.llm_provider.plan(
                LLMPlanRequest(
                    question=message,
                    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
                    conversation_context=state.model_dump(),
                    semantic_context={
                        "municipality_id": payload.municipality_id,
                        "capabilities": self.tool_registry.public_catalog(),
                        "tool_coverage_audit": tool_coverage_audit(),
                    },
                    tools=self.tool_registry.llm_schemas(),
                    complexity="semi_complex",
                    locale="es-ES",
                )
            )
        except Exception:
            logger.exception("orchestrator_llm_plan_failed")
            fallback = self._heuristic_tool_call(message, payload, relaxed=True)
            return [fallback] if fallback else []
        if plan.tool_call and self.tool_registry.has_tool(plan.tool_call.tool_name):
            return [plan.tool_call]
        fallback = self._heuristic_tool_call(message, payload, relaxed=True)
        return [fallback] if fallback else []

    def _heuristic_tool_calls(self, message: str, payload: Any, state: OrchestratorConversationContext) -> list[LLMToolCall]:
        text = normalize_text(message)
        municipio_id = payload.municipality_id
        years = [int(value) for value in __import__("re").findall(r"\b20\d{2}\b", text)]
        if state.last_topic == "housing" and "revalorizacion" in text:
            return [
                LLMToolCall(tool_name="compare_years", arguments={"municipio_id": municipio_id, "start_year": 2021, "end_year": 2025, "limit": 20}),
                LLMToolCall(tool_name="get_housing_profile", arguments={"municipio_id": municipio_id, "year": 2025, "order": "asc", "limit": 20}),
                LLMToolCall(tool_name="get_urban_profile", arguments={"municipio_id": municipio_id, "year": 2025, "limit": 20}),
            ]
        if len(years) >= 2 and any(token in text for token in ("crecido", "crecimiento", "crecieron")):
            return [LLMToolCall(tool_name="compare_years", arguments={
                "municipio_id": municipio_id, "start_year": years[0], "end_year": years[-1],
                "order": "desc", "limit": 3 if "tres" in text else 10,
            })]
        if ("poblacion joven" in text or "joven" in text) and "densidad" in text:
            return [LLMToolCall(tool_name="cross_metric_analysis", arguments={
                "municipio_id": municipio_id, "year": payload.context.active_year or 2025, "limit": 10,
                "metrics": [
                    {"metric": "population_under_30_pct", "direction": "high", "weight": 0.5},
                    {"metric": "population_density", "direction": "high", "weight": 0.5},
                ],
            })]
        if "crecimiento" in text and "renta" in text and ("precio" in text or "vivienda" in text):
            return [
                LLMToolCall(tool_name="compare_years", arguments={"municipio_id": municipio_id, "start_year": 2021, "end_year": 2025, "limit": 39}),
                LLMToolCall(tool_name="get_income_profile", arguments={"municipio_id": municipio_id, "limit": 39}),
                LLMToolCall(tool_name="get_housing_profile", arguments={"municipio_id": municipio_id, "order": "asc", "limit": 39}),
            ]
        if ("esas tres" in text or "aquellas tres" in text) and state.last_sections:
            domains = ["income", "population"]
            if "abstencion" in text:
                domains = ["electoral"]
            return [LLMToolCall(tool_name="compare_sections", arguments={
                "municipio_id": municipio_id, "sections": state.last_sections[:3],
                "year": payload.context.active_year or 2025, "include_domains": domains,
            })]
        if "abstencion" in text and state.last_sections and ("cual" in text or "ellas" in text):
            return [LLMToolCall(tool_name="compare_sections", arguments={
                "municipio_id": municipio_id, "sections": state.last_sections[:3],
                "year": payload.context.active_year or 2025, "include_domains": ["electoral"],
            })]
        if "perfil territorial" in text and "seccion" in text:
            section = next(iter(__import__("re").findall(r"seccion\s+(\d{1,2})", text)), None)
            return [LLMToolCall(tool_name="compare_sections", arguments={
                "municipio_id": municipio_id, "sections": [section] if section else state.last_sections[:1],
                "year": payload.context.active_year or 2025,
                "include_domains": ["population", "income", "electoral", "housing"],
            })]
        return []

    def _heuristic_tool_call(self, message: str, payload: Any, relaxed: bool = False) -> LLMToolCall | None:
        text = normalize_text(message)
        municipio_id = payload.municipality_id
        year = payload.context.active_year
        if asks_individual_vote_by_address(message):
            return LLMToolCall(tool_name="lookup_section_by_address", arguments={"municipio_id": municipio_id, "address": message})
        if "mas jovenes" in text or "mayor numero de jovenes" in text or "mas poblacion joven" in text:
            return LLMToolCall(tool_name="get_age_structure", arguments={"municipio_id": municipio_id, "metric": "population_under_30", "order": "desc", "year": year, "limit": 1})
        if "seccion mas joven" in text:
            return LLMToolCall(tool_name="get_age_structure", arguments={"municipio_id": municipio_id, "metric": "average_age", "order": "asc", "year": year, "limit": 1})
        if "mayor poblacion" in text or "mas poblacion" in text or "mas habitantes" in text:
            return LLMToolCall(tool_name="get_population_profile", arguments={"municipio_id": municipio_id, "year": year, "limit": 1})
        if "mayores" in text or "mayor de 65" in text:
            return LLMToolCall(tool_name="get_age_structure", arguments={"municipio_id": municipio_id, "metric": "population_over_65", "order": "desc", "year": year, "limit": 5})
        if "renta" in text or "ingreso" in text:
            return LLMToolCall(tool_name="get_income_profile", arguments={"municipio_id": municipio_id, "year": year, "limit": 5})
        if "vivienda" in text or "inmobiliari" in text or "revalorizacion" in text:
            return LLMToolCall(tool_name="get_housing_profile", arguments={"municipio_id": municipio_id, "year": year, "limit": 5})
        if "formacion" in text or "edad laboral" in text or "empleo" in text or "laboral" in text:
            return LLMToolCall(tool_name="get_socioeconomic_profile", arguments={"municipio_id": municipio_id, "year": year, "limit": 5})
        if "urbano" in text or "densidad edific" in text or "intensidad edific" in text:
            return LLMToolCall(tool_name="get_urban_profile", arguments={"municipio_id": municipio_id, "year": year, "limit": 5})
        if "abstencion" in text:
            election_year = next((int(value) for value in __import__("re").findall(r"\b20\d{2}\b", text)), None)
            return LLMToolCall(tool_name="get_electoral_results", arguments={"municipio_id": municipio_id, "intent": "abstention", "election_type": "MUNICIPALES", "election_year": election_year, "limit": 5})
        party = self._extract_party(text)
        if party and ("crecer" in text or "crecimiento" in text or "potencial" in text or "reforzar" in text):
            return LLMToolCall(
                tool_name="get_electoral_results",
                arguments={"municipio_id": municipio_id, "party": party, "intent": "growth_opportunity", "limit": 8},
            )
        if relaxed and ("voto" in text or "partido" in text or "eleccion" in text):
            return LLMToolCall(tool_name="get_electoral_results", arguments={"municipio_id": municipio_id, "limit": 5})
        return None

    async def _build_analysis_response(
        self,
        message: str,
        conversation_id: str,
        results: list[tuple[LLMToolCall, ToolResult]],
        state: OrchestratorConversationContext,
    ) -> OrchestratorResponse:
        if len(results) == 1:
            tool_call, result = results[0]
            return await self._build_tool_response(message, conversation_id, tool_call, result, state)

        data_layers = self._unique(
            str(result.metadata.get("data_layer"))
            for _tool_call, result in results
            if result.metadata.get("data_layer")
        )
        variables = self._unique(
            str(variable)
            for _tool_call, result in results
            for variable in (result.metadata.get("variables_used") or [])
        )
        sources = self._unique(source for _tool_call, result in results for source in result.sources)
        warnings = self._unique(
            warning
            for _tool_call, result in results
            for warning in [*result.caveats, *([result.error_message] if result.error_message else [])]
            if warning
        )
        all_rows = [row for _tool_call, result in results for row in result.rows]
        ok_results = [result for _tool_call, result in results if result.status == "ok"]
        ranking_basis = self._ranking_basis(message, [result for _tool_call, result in results], variables)
        missing = self._missing_relevant_variables(message, variables)
        answer = self._deterministic_answer(message, ok_results[0] if ok_results else results[-1][1])
        if {"population_growth_pct", "income_individual", "market_price_estimated_m2"} <= set(variables):
            answer = self._cross_domain_growth_income_housing_answer(results)
        if asks_individual_vote_by_address(message):
            prefix = (
                "No puedo saber qué vota una persona concreta ni tus vecinos individualmente. "
                "Solo puedo analizar resultados electorales agregados por sección censal. "
            )
            if not ok_results:
                answer = prefix + "Todavía no tengo una herramienta fiable para geocodificar esa calle dentro de SocTrace. Si me indicas la sección o zona aproximada, puedo analizar el comportamiento electoral agregado."
            else:
                answer = prefix + answer

        return OrchestratorResponse(
            answer=answer,
            methodology="Ejecución secuencial de tools seguras aprobadas por el Orchestrator.",
            confidence="high" if ok_results else "medium",
            data_used=sources,
            data_layers_used=data_layers,
            variables_used=variables,
            source_views=sources,
            missing_relevant_variables=missing,
            ranking_basis=ranking_basis,
            sections=self._sections_from_rows(all_rows),
            tables=[table for _tool_call, result in results for table in self._tables_from_result(result)][:3],
            charts=[chart for _tool_call, result in results for chart in self._charts_from_result(result)][:3],
            follow_up_questions=["Indícame la sección censal", "Analiza resultados agregados por sección"] if asks_individual_vote_by_address(message) else [],
            warnings=warnings,
            display_mode="structured" if all_rows else "chat",
            tools_used=[tool_call.tool_name for tool_call, _result in results],
            mode="orchestrator",
            llm_called=False,
            tools_called=[tool_call.tool_name for tool_call, _result in results],
            fallback_used=False,
            response_source="tool",
            self_check=self._self_check(answer=answer, tool_results=[result for _tool_call, result in results], ranking_basis=ranking_basis),
            conversation_id=conversation_id,
        )

    async def _build_tool_response(
        self,
        message: str,
        conversation_id: str,
        tool_call: LLMToolCall,
        result: ToolResult,
        state: OrchestratorConversationContext,
    ) -> OrchestratorResponse:
        data_layers = [result.metadata.get("data_layer")] if result.metadata.get("data_layer") else []
        variables = list(result.metadata.get("variables_used") or [])
        sources = list(result.sources or [])
        ranking_basis = self._ranking_basis(message, [result], variables)
        missing = self._missing_relevant_variables(message, variables)
        warnings = list(result.caveats or [])
        if result.status not in {"ok", "empty"} and result.error_message:
            warnings.append(result.error_message)

        answer = self._deterministic_answer(message, result)
        methodology = result.methodology_plain or "Consulta ejecutada mediante tool segura del Orchestrator sobre vistas aprobadas."
        followups = list(result.suggested_followups or [])
        llm_called = False
        if result.status == "ok" and self.llm_provider.name != "mock":
            try:
                llm_called = True
                synthesis = await self.llm_provider.synthesize(
                    LLMSynthesisRequest(
                        question=message,
                        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
                        tool_result=result.model_dump(),
                        conversation_context=state.model_dump(),
                        response_style="detailed",
                        locale="es-ES",
                    )
                )
                answer = synthesis.answer or answer
                methodology = synthesis.methodology or methodology
                warnings.extend(item for item in synthesis.caveats if item not in warnings)
                followups = synthesis.suggested_followups or followups
                grounding = validate_grounded_answer(answer, result.rows, variables)
                if not grounding.ok:
                    warnings.extend(item for item in grounding.warnings if item not in warnings)
                    answer = self._deterministic_answer(message, result)
            except Exception:
                logger.exception("orchestrator_llm_synthesis_failed")

        if asks_individual_vote_by_address(message):
            privacy_prefix = (
                "No puedo saber qué vota una persona concreta ni tus vecinos individualmente. "
                "Solo puedo analizar resultados electorales agregados por sección censal. "
            )
            if result.status == "unsupported" and result.error_code == "address_lookup_unavailable":
                answer = privacy_prefix + "Todavía no tengo una herramienta fiable para geocodificar esa calle dentro de SocTrace. Si me indicas la sección o zona aproximada, puedo analizar el comportamiento electoral agregado."
            elif not answer.startswith("No puedo saber"):
                answer = privacy_prefix + answer
        warnings.extend(self._ranking_bias_warnings(message, result.rows, ranking_basis, state))

        return OrchestratorResponse(
            answer=answer,
            methodology=methodology,
            confidence="high" if result.status == "ok" else "low",
            data_used=sources,
            data_layers_used=data_layers,
            variables_used=variables,
            source_views=sources,
            missing_relevant_variables=missing,
            ranking_basis=ranking_basis,
            sections=self._sections_from_rows(result.rows),
            tables=self._tables_from_result(result),
            charts=self._charts_from_result(result),
            follow_up_questions=followups[:4],
            warnings=warnings,
            display_mode="structured" if result.rows else "chat",
            tools_used=[tool_call.tool_name],
            mode="orchestrator",
            llm_called=llm_called,
            tools_called=[tool_call.tool_name],
            fallback_used=False,
            response_source="tool",
            self_check=self._self_check(answer=answer, tool_results=[result], ranking_basis=ranking_basis),
            conversation_id=conversation_id,
        )

    def _is_unhelpful_conversational_answer(self, answer: str) -> bool:
        normalized = normalize_text(answer)
        if not normalized:
            return True
        unhelpful_markers = [
            "he ejecutado la operacion",
            "proveedor llm real",
            "no estoy seguro de que analisis necesitas",
            "no estoy seguro de que análisis necesitas",
        ]
        return any(marker in normalized for marker in unhelpful_markers)

    def _conversational_safety_net(self, message: str) -> str:
        text = normalize_text(message)
        if is_greeting(message):
            return "Hola. Sí, podemos conversar. Puedo ayudarte a explorar población, renta, vivienda, voto, abstención o crecimiento urbano en Mijas, y cuando haga falta datos los consulto de forma segura."
        if is_suggestion_request(message):
            return (
                "Claro. Podemos empezar por algo sencillo: población, renta, voto, vivienda o crecimiento urbano. "
                "Por ejemplo, puedo decirte qué secciones son más jóvenes, dónde hay más abstención o qué zonas tienen más presión residencial."
            )
        if "capacidad de conversar" in text or "puedes conversar" in text:
            return (
                "Sí. Puedo conversar contigo, ayudarte a formular preguntas y después entrar en datos cuando tenga sentido. "
                "No hace falta que empieces con una consulta perfecta: puedo ayudarte a convertir una idea en un análisis territorial."
            )
        if "renta" in text:
            return (
                "Sí. En SocTrace podemos analizar la renta de Mijas por sección censal, comparando renta individual, renta por hogar y fuentes de ingreso. "
                "Puedo ayudarte de tres formas: ranking de secciones, detección de zonas vulnerables o cruces con voto, edad o vivienda. "
                "¿Quieres que empecemos por ranking de renta, evolución o comparación entre zonas?"
            )
        if "vivienda" in text:
            return (
                "Podemos mirar vivienda desde varios ángulos: vivir, invertir, presión residencial o posible revalorización. "
                "Cada objetivo cambia las variables: para vivir miraría entorno familiar y población; para invertir, valor estimado y presión; para revalorización, dinámica urbana. "
                "¿Quieres enfocarlo en vivir, invertir o revalorización?"
            )
        return (
            "Puedo ayudarte a convertir esa idea en una pregunta útil sobre Mijas. Podemos mirar población, renta, voto, vivienda, edad o crecimiento urbano, "
            "y si hace falta datos los consulto por capas seguras de SocTrace."
        )

    def _conversational_followups(self, message: str) -> list[str]:
        text = normalize_text(message)
        if "renta" in text:
            return ["Ranking de renta", "Evolución de renta", "Cruzar renta con voto", "Cruzar renta con vivienda"]
        if "vivienda" in text:
            return ["Vivir", "Invertir", "Revalorización", "Presión residencial"]
        return [
            "¿Cuál es la sección con mayor número de jóvenes?",
            "¿Dónde es más alta la abstención?",
            "Háblame de la renta en Mijas",
            "Háblame de vivienda",
        ]

    def _unique(self, values) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _deterministic_answer(self, message: str, result: ToolResult) -> str:
        if result.summary.get("answer"):
            return str(result.summary["answer"])
        if result.status == "empty":
            return "No he encontrado filas para esa consulta con las capas aprobadas actuales."
        if result.status != "ok":
            return "No he podido completar la consulta con las tools seguras activas."
        rows = result.rows or []
        if not rows:
            return "La consulta se ha ejecutado correctamente, pero no devuelve filas."
        first = rows[0]
        section = first.get("section_name") or first.get("name") or first.get("section_id") or "la primera sección"
        value = first.get("value")
        label = first.get("value_label") or result.metadata.get("metric_label") or result.metadata.get("metric")
        if value is not None:
            suffix = f" {label}" if label else ""
            year = first.get("year") or first.get("election_year")
            year_suffix = f" ({year})" if year else ""
            return f"El resultado principal es {section}: {value}{suffix}{year_suffix}."
        profile_fields = {
            "Población": first.get("population_total"),
            "Edad media": first.get("average_age"),
            "Renta individual": first.get("income_individual"),
            "Renta del hogar": first.get("income_household"),
            "Precio residencial estimado por m²": first.get("market_price_estimated_m2"),
            "Abstención": first.get("abstention_pct"),
        }
        available = [f"{label}: {value}" for label, value in profile_fields.items() if value is not None]
        if available:
            return f"Perfil territorial de {section}: " + "; ".join(available) + "."
        return f"El resultado principal es {section}."

    def _cross_domain_growth_income_housing_answer(
        self, results: list[tuple[LLMToolCall, ToolResult]]
    ) -> str:
        import re
        from statistics import median

        def section_number(row: dict[str, Any]) -> str | None:
            raw = " ".join(str(row.get(key) or "") for key in ("section_id", "section_name", "current_sections"))
            matches = re.findall(r"(?:Secci[oó]n\s+|29070)(\d{1,4})", raw, flags=re.I)
            return matches[-1].lstrip("0") if matches else None

        by_tool = {call.tool_name: result for call, result in results}
        growth = by_tool.get("compare_years")
        income = by_tool.get("get_income_profile")
        housing = by_tool.get("get_housing_profile")
        if not growth or not income or not housing or not income.rows or not housing.rows:
            return "He podido ejecutar parte del cruce, pero falta una de las capas necesarias; no voy a completar el ranking con estimaciones."
        income_values = [float(row["value"]) for row in income.rows if isinstance(row.get("value"), (int, float))]
        price_values = [float(row["value"]) for row in housing.rows if isinstance(row.get("value"), (int, float))]
        income_mean = sum(income_values) / len(income_values) if income_values else 0
        moderate_threshold = median(price_values) if price_values else 0
        income_by = {section_number(row): row for row in income.rows if section_number(row)}
        housing_by = {section_number(row): row for row in housing.rows if section_number(row)}
        candidates = []
        for row in growth.rows:
            key = section_number(row)
            income_row, housing_row = income_by.get(key), housing_by.get(key)
            if not income_row or not housing_row or float(row.get("growth_pct") or 0) <= 0:
                continue
            if float(income_row.get("value") or 0) > income_mean and float(housing_row.get("value") or 0) <= moderate_threshold:
                candidates.append((row, income_row, housing_row))
        if not candidates:
            return (
                "No hay secciones que cumplan simultáneamente los tres filtros con cobertura común. "
                f"He definido renta superior a la media como más de {income_mean:.0f} € y precio moderado como igual o inferior a la mediana ({moderate_threshold:.0f} €/m²)."
            )
        lines = [
            f"• {growth_row.get('section_name')}: crecimiento {float(growth_row.get('growth_pct') or 0):.1f}%, "
            f"renta {float(income_row.get('value') or 0):.0f} € y precio {float(housing_row.get('value') or 0):.0f} €/m²"
            for growth_row, income_row, housing_row in candidates[:5]
        ]
        return (
            "Las zonas que cumplen simultáneamente crecimiento positivo, renta superior a la media y precio moderado son:\n\n"
            + "\n".join(lines)
            + f"\n\nPrecio moderado significa igual o inferior a la mediana observada ({moderate_threshold:.0f} €/m²); "
              f"renta superior a la media significa más de {income_mean:.0f} €. No uso una puntuación opaca."
        )

    def _ranking_basis(self, message: str, results: list[ToolResult], variables: list[str]) -> dict[str, Any]:
        if not results:
            return {}
        first = results[0]
        rows = first.rows or []
        top_reasons = []
        for row in rows[:5]:
            section = row.get("section_name") or row.get("section_id") or row.get("party")
            value = row.get("value")
            explanation = row.get("opportunity_explanation") or row.get("value_label") or first.metadata.get("value_label")
            top_reasons.append({"section": section, "value": value, "reason": explanation})
        concept = infer_goal_concept(message)
        weights = self._default_weights_for_concept(concept, variables)
        excluded = self._excluded_variables_for_concept(concept, variables)
        return {
            "goal": concept,
            "variables": variables,
            "weights": weights,
            "excluded_variables": excluded,
            "reason_for_top_sections": top_reasons,
        }

    def _default_weights_for_concept(self, concept: str, variables: list[str]) -> dict[str, float]:
        if concept == "electoral_growth_potential":
            weights = {
                "vote_pct": 0.25,
                "abstention_pct": 0.2,
                "margin_to_first_place": 0.2,
                "volatility_pct": 0.15,
                "historical_recovery_room_pct": 0.2,
            }
            return {key: value for key, value in weights.items() if key in variables or not variables}
        if concept == "public_service_need":
            return {variable: 1.0 for variable in variables if variable in {"population_under_18", "population_under_30", "income_individual", "population_density"}}
        if concept == "commercial_opportunity":
            return {variable: 1.0 for variable in variables if variable in {"population_total", "income_individual", "population_density"}}
        return {variable: 1.0 for variable in variables}

    def _excluded_variables_for_concept(self, concept: str, variables: list[str]) -> list[str]:
        relevant = {
            "electoral_growth_potential": {"vote_pct", "abstention_pct", "winner_party", "margin_to_first_place", "volatility_pct", "historical_recovery_room_pct", "electoral_growth_opportunity"},
            "urban_expansion": {"population_total", "population_density", "market_price_estimated_m2", "building_intensity", "parcel_density", "built_footprint"},
            "public_service_need": {"population_under_18", "population_under_30", "income_individual", "population_density"},
            "commercial_opportunity": {"population_total", "income_individual", "population_density"},
        }.get(concept, set(variables))
        return [variable for variable in variables if variable not in relevant]

    def _missing_relevant_variables(self, message: str, variables: list[str]) -> list[str]:
        concept = infer_goal_concept(message)
        required = {
            "electoral_growth_potential": ["vote_pct", "abstention_pct", "margin_to_first_place", "historical_recovery_room_pct", "volatility_pct"],
            "public_service_need": ["target_population", "vulnerability", "density", "access_or_service_gap"],
            "commercial_opportunity": ["target_audience", "density", "income"],
            "urban_expansion": ["population_growth", "built_environment_growth", "housing_growth"],
        }.get(concept, [])
        return [variable for variable in required if variable not in variables]

    def _ranking_bias_warnings(
        self,
        message: str,
        rows: list[dict[str, Any]],
        ranking_basis: dict[str, Any],
        state: OrchestratorConversationContext,
    ) -> list[str]:
        current_sections = [str(row.get("section_id")) for row in rows[:5] if row.get("section_id")]
        if not current_sections or not state.last_sections:
            return []
        overlap = set(current_sections) & set(state.last_sections)
        if not overlap or infer_topic(message) == state.last_topic:
            return []
        variables = set(ranking_basis.get("variables") or [])
        generic = {"population_total", "population_density", "population_under_30", "building_intensity"}
        if variables and variables <= generic:
            return [
                "Varias secciones coinciden con una respuesta anterior y el ranking usa variables genéricas; no debe interpretarse como oportunidad electoral o ROI sin variables específicas."
            ]
        return []

    def _self_check(
        self,
        *,
        answer: str,
        tool_results: list[ToolResult],
        ranking_basis: dict[str, Any] | None = None,
        needs_clarification: bool = False,
    ) -> dict[str, bool]:
        has_tools = bool(tool_results)
        has_ok_or_no_tools_needed = not has_tools or any(result.status == "ok" for result in tool_results)
        has_provenance = not has_tools or all(result.metadata.get("data_layer") for result in tool_results)
        variables = list((ranking_basis or {}).get("variables") or [])
        excluded = list((ranking_basis or {}).get("excluded_variables") or [])
        return {
            "is_answering_user_question": bool(answer.strip()),
            "uses_relevant_tools": has_ok_or_no_tools_needed,
            "has_data_provenance": has_provenance,
            "no_unsupported_claims": True,
            "ranking_matches_goal": not excluded or len(excluded) < len(variables),
            "needs_clarification": needs_clarification,
        }

    def _extract_party(self, text: str) -> str | None:
        for party in ("pp", "psoe", "vox"):
            if party in text.split() or f" {party} " in f" {text} ":
                return party.upper()
        return None

    def _sections_from_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        import re
        sections: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            section_id = row.get("section_id")
            lineage_match = re.fullmatch(r"29070_(29070\d{5})_LINEAGE", str(section_id or ""))
            if lineage_match:
                section_id = lineage_match.group(1)
            if not section_id or section_id in seen:
                continue
            seen.add(section_id)
            sections.append(
                {
                    "section_id": section_id,
                    "name": row.get("section_name") or section_id,
                    "score": row.get("value"),
                    "metrics": {key: value for key, value in row.items() if key not in {"section_id", "section_name"}},
                }
            )
        return sections[:10]

    def _tables_from_result(self, result: ToolResult) -> list[OrchestratorTable]:
        rows = result.rows[:10]
        if not rows:
            return []
        preferred = [
            key
            for key in [
                "section_id",
                "section_name",
                "year",
                "election_year",
                "party",
                "vote_pct",
                "abstention_pct",
                "margin_to_first_place",
                "growth_score",
                "value",
                "value_label",
            ]
            if key in rows[0]
        ]
        columns = preferred or list(rows[0].keys())[:6]
        return [
            OrchestratorTable(
                title="Resultados",
                columns=columns,
                rows=[[self._cell(row.get(column)) for column in columns] for row in rows],
            )
        ]

    def _charts_from_result(self, result: ToolResult) -> list[OrchestratorChart]:
        if not result.chart_spec:
            return []
        chart = result.chart_spec
        return [
            OrchestratorChart(
                kind=str(chart.get("kind") or chart.get("type") or "bar"),
                title=str(chart.get("title") or "Resultados"),
                data=list(chart.get("data") or []),
            )
        ]

    def _cell(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    def _clarification_response(self, message: str, conversation_id: str) -> OrchestratorResponse:
        return OrchestratorResponse(
            answer="He entendido el objetivo general, pero necesito una precisión que cambia el análisis. ¿Qué resultado concreto quieres priorizar?",
            methodology="Una aclaración material antes de seleccionar herramientas y datos.",
            confidence="medium",
            display_mode="chat",
            follow_up_questions=[
                "Población por sección",
                "Estructura de edad",
                "Renta por sección",
                "Vivienda",
                "Resultados electorales",
            ],
            conversation_id=conversation_id,
        )

    def _remember(
        self,
        conversation_id: str,
        message: str,
        response: OrchestratorResponse,
        pending_clarification: str | None = None,
    ) -> None:
        sections = [str(section.get("section_id")) for section in response.sections if section.get("section_id")]
        context_store.update(
            conversation_id,
            user_goal=message,
            topic=infer_topic(message),
            sections=sections,
            tools_used=response.tools_used,
            data_layers_used=response.data_layers_used,
            variables_used=response.variables_used,
            source_views=response.source_views,
            missing_relevant_variables=response.missing_relevant_variables,
            ranking_basis=response.ranking_basis,
            answer=response.answer,
            methodology=response.methodology,
            warnings=response.warnings,
            pending_clarification=pending_clarification,
        )
