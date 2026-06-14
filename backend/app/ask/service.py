import json
import logging
import re
import time
import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends
from sqlalchemy.orm import Session

from app.ask.conversation import ConversationState, PersistentConversationStore, conversation_memory_to_state, conversation_store
from app.ask.conversation.conversation_state import (
    ElectionContext,
    LastAnswerContext,
    MunicipalityContext,
    ConversationSection,
)
from app.ask.conversation.follow_up_resolver import FollowUpResolver, FollowUpResolution
from app.ask.conversation.conversational_policy import ConversationalPolicyLayer
from app.ask.answer_guard import AnswerGuard
from app.ask.interpreter import AnalyticalIntent, QuestionInterpreter
from app.ask.llm.complexity_router import ComplexityRouter
from app.ask.llm.factory import get_llm_provider
from app.ask.llm.provider import LLMProvider
from app.ask.orchestration import AgentExecutionPlan, AgentPlanStep, AnswerCheck
from app.ask.planner import ExecutionPlan, SocTracePlanner
from app.ask.planner_loop import AskPlannerLoop
from app.ask.reference_resolver import resolve_references
from app.ask.sql import QueryExecutor, SemanticPlan, SqlGenerator, SqlValidator
from app.ask.semantic_layer import AnalyticalOperation
from app.ask.rendering.answer_formatter_v2 import AnswerFormatterV2
from app.ask.suggestions import SuggestionRegistry, SuggestionValidator
from app.ask.tools import ToolRegistry, build_tool_registry
from app.ask.tools.registry import _election_label
from app.ask.tools_v2 import ToolContext, ToolExecutorV2, ToolRegistryV2, ToolResult, tool_call_from_operation
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.schemas.ask import AskRequest, AskResponse
from app.services.local_analyst_service import extract_metric_direction, extract_party, extract_section_hint, normalize


logger = logging.getLogger(__name__)
CONVERSATION_STATE = conversation_store._states

ASK_SOCTRACE_SYSTEM_PROMPT = """
You are Ask soctrace, a municipal territorial intelligence analyst for Mijas.

You can answer analytical questions by generating safe read-only SQL against the approved soctrace semantic catalog.
You do not invent numbers.
If data is unavailable, say what is missing.
You explain methodology in clear language.
You avoid raw SQL unless the user explicitly asks for SQL.
You return analytical, concise and decision-oriented answers.

Rules:
- Never answer numerical questions without calling a data tool.
- When the user asks for a number, ranking, comparison, correlation, average, total, trend or segmentation, generate or execute an analytical query.
- Use approved views only.
- Do not answer with "I do not have a specific tool" unless the semantic catalog truly lacks the required data.
- Never assume unavailable data.
- For electoral questions, use normalized party names.
- For demographic questions, use demographic tools.
- For socioeconomic questions, combine available indicators.
- For historical questions, use all available years/elections.
- If a question combines age range, abstention/voting, sections and an election context, use age_cohort_abstention_by_section instead of demographics_age_range.
- Always explain whether the result is exact or estimated.
- Return the final answer as JSON with keys: answer, data, methodology, caveats, sources, suggestedFollowUps.
""".strip()


class AskSocTraceService:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.registry = build_tool_registry(session)
        self.planner = SocTracePlanner()
        self.question_interpreter = QuestionInterpreter(
            openai_api_key=settings.openai_api_key,
            openai_model=settings.openai_model,
            timeout_seconds=settings.openai_timeout_seconds,
        )
        self.sql_generator = SqlGenerator()
        self.sql_validator = SqlValidator(self.sql_generator.approved_relations)
        self.query_executor = QueryExecutor(session)
        self.persistent_conversation_store = PersistentConversationStore(session)
        self.persistent_memory_available = True
        self.tools_v2_registry = ToolRegistryV2(self.query_executor, self.sql_validator, self.sql_generator.semantic_catalog)
        self.tools_v2_executor = ToolExecutorV2(self.tools_v2_registry)
        llm_provider_name = settings.ask_llm_provider or settings.llm_provider
        self.llm_provider: LLMProvider = get_llm_provider(
            llm_provider_name,
            fallback_to_mock=not settings.ask_use_llm_planner,
        )
        self.llm_provider_health = self.llm_provider.healthcheck()
        self.complexity_router = ComplexityRouter()
        self.answer_guard = AnswerGuard()
        self.answer_formatter_v2 = AnswerFormatterV2()
        self.follow_up_resolver = FollowUpResolver()
        self.conversational_policy = ConversationalPolicyLayer()
        self.suggestion_registry = SuggestionRegistry()
        self.suggestion_validator = SuggestionValidator(
            registry=self.suggestion_registry,
            tool_registry=self.tools_v2_registry,
            tool_executor=self.tools_v2_executor,
            operation_interpreter=self.sql_generator.operation_interpreter,
        )
        self.planner_loop = AskPlannerLoop(
            provider=self.llm_provider,
            complexity_router=self.complexity_router,
            tool_registry=self.tools_v2_registry,
            tool_executor=self.tools_v2_executor,
            follow_up_resolver=self.follow_up_resolver,
            answer_guard=self.answer_guard,
            settings=settings,
            persistent_store=self.persistent_conversation_store,
        )
        self._selected_tool_names: list[str] = []
        self._tool_inputs: list[dict[str, Any]] = []
        self._conversation_id: str | None = None
        self._resolved_references: dict[str, Any] = {}
        self._execution_plan: ExecutionPlan | None = None
        self._analytical_intent: AnalyticalIntent | None = None
        self._deterministic_match: AnalyticalIntent | None = None
        self._skip_followup_once = False

    def ask(self, payload: AskRequest) -> AskResponse:
        started_at = time.monotonic()
        question = (payload.question or "").strip()
        if not payload.conversationId:
            payload.conversationId = str(uuid4())
        self._conversation_id = payload.conversationId
        self._selected_tool_names = []
        self._tool_inputs = []
        self._execution_plan = None
        self._analytical_intent = None
        self._deterministic_match = None
        error: str | None = None
        try:
            state = self._ensure_state(payload)
            if not hasattr(self, "follow_up_resolver"):
                self.follow_up_resolver = FollowUpResolver()
            if not getattr(self, "_skip_followup_once", False):
                followup_response = self._followup_context_response(payload, state)
                if followup_response:
                    if followup_response.session_memory:
                        return followup_response
                    return self._with_session_memory(payload, followup_response)
            self._skip_followup_once = False
            previous_response = self._previous_context_response(payload, state)
            if previous_response:
                return self._with_session_memory(payload, previous_response)
            policy_response = self._ask_with_conversational_policy(payload, state)
            if policy_response:
                return self._with_session_memory(payload, policy_response)
            custom_response = self._ask_with_custom_analyses(payload, state)
            if custom_response:
                return self._with_session_memory(payload, custom_response)
            llm_response = self._ask_with_llm_planner(payload)
            if llm_response:
                return self._with_session_memory(payload, llm_response)
            self._resolved_references = resolve_references(question, state)
            self._deterministic_match = self.question_interpreter.deterministic_match(question)
            self._analytical_intent = self._deterministic_match or self.question_interpreter.interpret(
                question,
                self.sql_generator.catalog,
            )
            tools_v2_response = self._ask_with_tools_v2(payload)
            if tools_v2_response:
                return self._with_session_memory(payload, tools_v2_response)
            agent_response = self._run_agent_loop(payload, state)
            if agent_response:
                return self._with_session_memory(payload, agent_response)
            self._execution_plan = self.planner.build_plan(
                question,
                self._resolved_references,
                payload.activeMunicipality,
            )
            if self._execution_plan:
                response = self._execute_plan(payload, self._execution_plan)
                return self._with_session_memory(payload, response)
            semantic_response = self._ask_with_semantic_sql(payload)
            if semantic_response:
                return self._with_session_memory(payload, semantic_response)
            if self.settings.openai_api_key:
                response = self._ask_with_openai(payload)
            else:
                response = self._ask_with_fallback(payload)
            return self._with_session_memory(payload, response)
        except Exception as exc:
            logger.exception("Ask soctrace failed")
            error = str(exc)
            return self._with_session_memory(payload, AskResponse(
                answer="No he podido acceder temporalmente a los datos necesarios para responder la consulta.",
                methodology="No se han inferido datos ausentes ni se ha usado informacion externa.",
                caveats=["El detalle técnico queda registrado internamente para revisión."],
                sources=[],
                suggestedFollowUps=["Reintentar la consulta en unos minutos.", "Probar con otra pregunta de población o secciones."],
            ))
        finally:
            logger.info(
                "ask_soctrace",
                extra={
                    "question": question,
                    "selectedToolNames": self._selected_tool_names,
                    "toolInputs": self._tool_inputs,
                    "conversationId": payload.conversationId,
                    "resolvedReferences": self._resolved_references,
                    "deterministicMatch": self._deterministic_match.model_dump() if self._deterministic_match else None,
                    "analyticalIntent": self._analytical_intent.model_dump() if self._analytical_intent else None,
                    "executionPlan": self._execution_plan.model_dump() if self._execution_plan else None,
                    "toolsExecuted": self._selected_tool_names,
                    "responseTimeMs": round((time.monotonic() - started_at) * 1000),
                    "model": self.settings.openai_model if self.settings.openai_api_key else "deterministic-fallback",
                    "error": error,
                },
            )

    def _run_agent_loop(self, payload: AskRequest, state: ConversationState | None) -> AskResponse | None:
        if state is None:
            return None
        plan = self._create_agent_execution_plan(payload, state)
        if plan is None or plan.task == "unknown":
            return None

        conversation_before = state.model_dump()
        sql_results: dict[str, list[dict[str, Any]]] = {}
        executed: list[dict[str, Any]] = []
        answer_check = AnswerCheck(passed=False, missing=["not executed"])
        try:
            if not self._validate_agent_plan(plan):
                answer_check = AnswerCheck(passed=False, missing=["required conversation context"])
                return self._agent_check_failed_response(plan, answer_check)

            for step in plan.steps:
                if step.type != "sql":
                    continue
                sql = str(step.input.get("sql") or "")
                validation = self.sql_validator.validate(sql)
                executed.append({"id": step.id, "name": step.name, "validation": {"ok": validation.ok, "error": validation.error}})
                if not validation.ok:
                    answer_check = AnswerCheck(passed=False, missing=[f"sql validation failed: {validation.error}"])
                    return self._agent_check_failed_response(plan, answer_check)
                rows = self.query_executor.execute(sql)
                sql_results[step.id] = rows
                executed[-1]["rowCount"] = len(rows)

            answer_check = self._answer_current_question_check(plan, sql_results)
            if not answer_check.passed:
                return self._agent_check_failed_response(plan, answer_check)

            response = self._render_agent_answer(plan, sql_results)
            self._remember_agent_result(payload, plan, sql_results)
            return response
        finally:
            if self.settings.app_env == "development":
                logger.info(
                    "ask_soctrace_agent_loop",
                    extra={
                        "question": payload.question,
                        "resolvedQuestion": plan.resolvedQuestion,
                        "conversationStateBefore": conversation_before,
                        "executionPlan": plan.model_dump(),
                        "toolsOrSqlExecuted": executed,
                        "answerCheck": answer_check.model_dump(),
                        "renderer": plan.renderer,
                    },
                )

    def _ask_with_conversational_policy(self, payload: AskRequest, state: ConversationState | None) -> AskResponse | None:
        if not hasattr(self, "tools_v2_executor"):
            return None
        context_dict = state.model_dump() if state else {}
        decision = self.conversational_policy.resolve(
            payload.question or "",
            semantic_interpretation=self._deterministic_match.model_dump() if self._deterministic_match else None,
            conversation_context=context_dict,
        )
        if decision.action == "clarify_with_options":
            return AskResponse(
                answer=decision.explanation_to_user or "Puedo darte una aproximación con los datos disponibles si eliges una opción.",
                confidence=decision.confidence,
                data={
                    "policy_action": decision.action,
                    "rewritten_question": decision.rewritten_question,
                    "preferred_tool": decision.preferred_tool,
                    "preferred_arguments": decision.preferred_arguments,
                    "ctas": [
                        {"label": "Calcular viabilidad electoral orientativa", "question": decision.rewritten_question or "Calcular viabilidad electoral orientativa"},
                        {"label": "Comparar con PSOE", "question": "Comparar viabilidad electoral del PP y PSOE"},
                        {"label": "Ver secciones prioritarias", "question": "¿Qué secciones debería priorizar el PP?"},
                    ],
                },
                methodology="Capa conversacional: si falta una probabilidad exacta, ofrezco un proxy calculable con datos internos.",
                caveats=["No es una probabilidad estadística real ni una predicción de sondeo."],
                suggestedFollowUps=[
                    "Calcular viabilidad electoral orientativa",
                    "Comparar con PSOE",
                    "Ver secciones prioritarias",
                ],
            )
        if decision.action not in {"proxy_analysis", "scenario_estimate", "direct_tool"}:
            return None
        supported_policy_tools = {
            "electoral_viability_estimate",
            "electoral_growth_opportunity",
            "mobilizable_abstention_opportunity",
        }
        if decision.preferred_tool not in supported_policy_tools:
            return None
        arguments = {
            "municipio_id": payload.activeMunicipality or "29070",
            **decision.preferred_arguments,
        }
        context = ToolContext(
            municipio_id=payload.activeMunicipality or "29070",
            municipio_nombre="Mijas" if (payload.activeMunicipality or "29070") == "29070" else None,
            active_year=payload.activeYear,
            conversation_id=payload.conversationId,
        )
        result = self.tools_v2_executor.execute_sync(decision.preferred_tool, arguments, context)
        if result.status in {"unsupported", "error"}:
            return None
        operation_name = str(decision.preferred_tool)
        metric_by_tool = {
            "electoral_viability_estimate": "electoral_viability",
            "electoral_growth_opportunity": "electoral_growth_opportunity",
            "mobilizable_abstention_opportunity": "mobilizable_abstention",
        }
        metric_name = metric_by_tool.get(operation_name, operation_name)
        operation = AnalyticalOperation(
            operation=operation_name,
            metric=metric_name,
            municipio_id=payload.activeMunicipality or "29070",
            municipality_id=payload.activeMunicipality or "29070",
            party=arguments.get("party") if arguments.get("party") in {"PP", "PSOE", "VOX"} else None,
            filters={"target": arguments.get("target")} if arguments.get("target") else {},
            election_type=arguments.get("election_type") or "MUNICIPALES",
            year=arguments.get("baseline_year") or arguments.get("election_year"),
            output="table",
            confidence=decision.confidence,
            explanation=decision.explanation_to_user or "",
        )
        self._remember_tool_v2_result(payload, operation, result)
        response = self._render_tool_v2_response(payload, operation, result)
        if decision.explanation_to_user and decision.explanation_to_user not in response.answer:
            response.answer = f"{response.answer}"
        return response

    def _ask_with_custom_analyses(self, payload: AskRequest, state: ConversationState | None) -> AskResponse | None:
        question = payload.question or ""
        text = normalize(question)
        municipality_id = payload.activeMunicipality or "29070"
        age_range = self.sql_generator.operation_interpreter._age_range_count(question)
        section_hint = extract_section_hint(question) or self._section_hint_from_question(question)
        if age_range and section_hint:
            return self._section_age_range_response(payload, municipality_id, section_hint, age_range)
        if re.search(r"partido.*domina.*seccion mas joven|partido.*domina.*sección más joven|partido.*fuerte.*seccion mas joven|partido.*fuerte.*sección más joven", text):
            return self._youngest_section_party_dominance_response(payload, municipality_id)
        if re.search(r"reducido.*participacion|reducido.*participación|participacion.*reducido|participación.*reducido|caido.*participacion|caído.*participación", text):
            return self._participation_decline_response(payload, municipality_id)
        if re.search(r"cambian.*partido ganador|cambia.*partido ganador|ganador.*segun la eleccion|ganador.*según la elección", text):
            return self._winner_switch_response(payload, municipality_id)
        if re.search(r"perdi[oó].*apoyo|gan[oó].*apoyo|creci[oó].*vox|cambiaron m[aá]s entre", text):
            return self._electoral_evolution_response(payload, municipality_id)
        if re.search(r"podrian aumentar la abstencion|podrían aumentar la abstención|riesgo.*abstencion|riesgo.*abstención", text):
            return self._abstention_increase_risk_response(payload, municipality_id)
        return None

    def _section_hint_from_question(self, question: str) -> str | None:
        match = re.search(r"\ben\s+([^?]+)$", question.strip(), flags=re.IGNORECASE)
        if match:
            hint = match.group(1).strip(" .¿?\"'")
            if hint and not re.fullmatch(r"20\d{2}|19\d{2}", hint):
                return hint
        text = normalize(question)
        if "riviera sur" in text:
            return "Riviera Sur"
        return None

    def _section_age_range_response(self, payload: AskRequest, municipality_id: str, section_hint: str, age_range: tuple[int, int]) -> AskResponse | None:
        min_age, max_age = age_range
        section_sql = section_hint.replace("'", "''")
        sql = f"""
WITH target AS (
    SELECT section_id, section_name, municipio_id, municipio_nombre
    FROM marts.agent_section_lookup
    WHERE municipio_id = '{municipality_id}'
      AND (
        LOWER(section_name) LIKE LOWER('%{section_sql}%')
        OR LOWER(display_name) LIKE LOWER('%{section_sql}%')
      )
    ORDER BY section_name
    LIMIT 1
),
latest AS (
    SELECT MAX(year) AS year
    FROM marts.agent_population_age
    WHERE municipio_id = '{municipality_id}'
),
age_rows AS (
    SELECT
        target.section_id,
        target.section_name,
        target.municipio_id,
        target.municipio_nombre,
        age.year,
        age.age_min,
        age.age_max,
        SUM(age.people)::numeric AS people
    FROM target
    JOIN marts.agent_population_age age
      ON age.section_id = target.section_id
     AND age.municipio_id = target.municipio_id
    JOIN latest USING (year)
    WHERE age.gender IN ('H', 'M')
      AND age.age_max >= {int(min_age)}
      AND age.age_min <= {int(max_age)}
    GROUP BY target.section_id, target.section_name, target.municipio_id, target.municipio_nombre, age.year, age.age_min, age.age_max
)
SELECT
    section_id,
    section_name,
    municipio_id,
    municipio_nombre,
    year,
    {int(min_age)} AS min_age,
    {int(max_age)} AS max_age,
    SUM(people)::bigint AS value
FROM age_rows
GROUP BY section_id, section_name, municipio_id, municipio_nombre, year
LIMIT 1
""".strip()
        rows = self.query_executor.execute(sql)
        if not rows:
            return None
        row = rows[0]
        answer = (
            f"En {row.get('section_name')} viven aproximadamente {_format_int(row.get('value'))} personas entre {min_age} y {max_age} años en {row.get('year')}.\n\n"
            "Qué significa\n\nEs una estimación demográfica por tramo de edad dentro de una sección concreta.\n\n"
            "Cómo se ha calculado\n\nSumo las cohortes de edad disponibles que se solapan con el rango solicitado. La fuente trabaja con tramos agrupados, por lo que el resultado es aproximado cuando el rango no coincide exactamente con los cortes de edad.\n\n"
            "Cautela metodológica\n\nNo es un padrón individual; es una agregación territorial por sección y cohorte."
        )
        self._selected_tool_names.append("section_age_range")
        self._tool_inputs.append({"section_age_range": {"municipio_id": municipality_id, "section": section_hint, "min_age": min_age, "max_age": max_age}})
        return AskResponse(
            answer=answer,
            confidence="medium",
            resultType="single_value",
            entities=self._custom_entities(rows, "value"),
            data={"tool": "section_age_range", "operation": "section_age_range", "rows": rows},
            methodology="Suma de cohortes de edad disponibles que se solapan con el rango solicitado en la sección resuelta.",
            caveats=["Estimación aproximada si las cohortes quinquenales no encajan exactamente con el rango."],
            sources=["marts.agent_population_age", "marts.agent_section_lookup"],
            table=self._custom_table("Personas por rango de edad en sección", rows),
            chartSpec={"type": "metric", "title": f"Población {min_age}-{max_age}", "value": row.get("value"), "rows": rows},
        )

    def _custom_table(self, title: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        table_rows = rows[:15]
        if not table_rows:
            return None
        columns = list(table_rows[0].keys())
        return {"title": title, "columns": columns, "rows": [[row.get(column) for column in columns] for row in table_rows]}

    def _custom_entities(self, rows: list[dict[str, Any]], label_key: str = "value") -> list[Any]:
        entities = []
        for row in rows:
            if row.get("section_id") and row.get("section_name"):
                value = row.get(label_key)
                label = _format_decimal(value, 1) if isinstance(value, (int, float)) else str(value or "")
                entities.append(self._section_entity(row, label))
        return entities

    def _youngest_section_party_dominance_response(self, payload: AskRequest, municipality_id: str) -> AskResponse | None:
        rows = self.query_executor.execute(self._party_history_for_youngest_section_sql(municipality_id))
        if not rows:
            return None
        first = rows[0]
        ranking = "\n".join(
            f"• {row.get('party')}: {_format_decimal(row.get('average_vote_pct'), 1)}% medio; "
            f"{_format_int(row.get('first_place_count'))} primeras posiciones en {row.get('elections_included')} elecciones"
            for row in rows[:6]
        )
        youngest = first.get("youngest_section_name")
        answer = (
            f"La sección más joven es {youngest}, con una edad media de {_format_decimal(first.get('youngest_average_age'), 1)} años. "
            f"Si analizamos su comportamiento electoral histórico, el partido con mayor fortaleza media en esa sección es {first.get('party')}.\n\n"
            f"Indicadores principales\n\n{ranking}\n\n"
            "Qué significa\n\nLa pregunta requiere encadenar dos análisis: primero identificar la sección con menor edad media y después revisar el historial electoral de esa sección.\n\n"
            "Cómo se ha calculado\n\nOrdeno las secciones por edad media ascendente en el último año demográfico disponible. Después calculo la media histórica de porcentaje de voto por partido en esa sección y cuento cuántas veces cada partido fue primera fuerza.\n\n"
            "Lectura estratégica\n\nEsta lectura ayuda a cruzar perfil demográfico y fortaleza electoral territorial. No implica que las personas jóvenes voten a ese partido; describe el comportamiento agregado de la sección.\n\n"
            "Cautela metodológica\n\n• Es una inferencia territorial por sección, no voto individual por edad.\n"
            "• La media histórica mezcla elecciones disponibles comparables en el dataset."
        )
        self._selected_tool_names.append("chained_youngest_section_party_dominance")
        self._tool_inputs.append({"chained_youngest_section_party_dominance": {"municipio_id": municipality_id}})
        return AskResponse(
            answer=answer,
            confidence="high",
            resultType="entity_list",
            entities=self._custom_entities(rows, "average_vote_pct"),
            data={"tool": "chained_youngest_section_party_dominance", "operation": "chained_query", "rows": rows},
            methodology="rank_sections(average_age asc limit 1) y media histórica electoral por partido en la sección resultante.",
            caveats=["No interpreta voto individual por edad."],
            sources=["marts.agent_section_profile", "marts.agent_electoral_results"],
            table=self._custom_table("Partidos en la sección más joven", rows),
            chartSpec={"type": "bar", "title": "Fortaleza histórica en la sección más joven", "x": "party", "y": "average_vote_pct", "rows": rows},
        )

    def _participation_decline_response(self, payload: AskRequest, municipality_id: str) -> AskResponse | None:
        sql = f"""
WITH years AS (
    SELECT 2019::integer AS start_year, 2023::integer AS end_year
),
base AS (
    SELECT section_id, section_name, municipio_id, municipio_nombre, election_year, participation_pct
    FROM marts.agent_electoral_summary
    WHERE municipio_id = '{municipality_id}'
      AND election_type = 'MUNICIPALES'
      AND election_year IN (2019, 2023)
      AND participation_pct IS NOT NULL
),
pivot AS (
    SELECT
        section_id,
        MAX(section_name) AS section_name,
        MAX(municipio_id) AS municipio_id,
        MAX(municipio_nombre) AS municipio_nombre,
        MAX(participation_pct) FILTER (WHERE election_year = 2019) AS participation_start,
        MAX(participation_pct) FILTER (WHERE election_year = 2023) AS participation_end
    FROM base
    GROUP BY section_id
)
SELECT
    section_id,
    section_name,
    municipio_id,
    municipio_nombre,
    2019 AS start_year,
    2023 AS end_year,
    ROUND(participation_start::numeric, 2) AS participation_start,
    ROUND(participation_end::numeric, 2) AS participation_end,
    ROUND((participation_end - participation_start)::numeric, 2) AS delta_pp,
    ABS(ROUND((participation_end - participation_start)::numeric, 2)) AS value
FROM pivot
WHERE participation_start IS NOT NULL AND participation_end IS NOT NULL
ORDER BY delta_pp ASC, section_name
LIMIT 10
""".strip()
        rows = self.query_executor.execute(sql)
        if not rows:
            return None
        first = rows[0]
        ranking = "\n".join(
            f"• {row.get('section_name')} — {_format_signed_decimal(row.get('delta_pp'), 1)} p.p.; "
            f"{_format_decimal(row.get('participation_start'), 1)}% en 2019 → {_format_decimal(row.get('participation_end'), 1)}% en 2023"
            for row in rows[:8]
        )
        answer = (
            f"La mayor reducción de participación entre las municipales de 2019 y 2023 aparece en {first.get('section_name')}.\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            "Qué significa\n\nMido la caída de participación como diferencia en puntos porcentuales entre dos elecciones municipales comparables.\n\n"
            "Cómo se ha calculado\n\nComparo `participation_pct` por sección en municipales 2019 frente a municipales 2023 y ordeno de mayor descenso a menor descenso.\n\n"
            "Interpretación útil\n\nUna bajada fuerte puede señalar desmovilización, cambios de contexto electoral o transformación territorial. Puedo cruzarlo con cambios demográficos o renta para explorar posibles explicaciones.\n\n"
            "Cautela metodológica\n\n• No atribuye causalidad.\n"
            "• Compara secciones disponibles en ambos años; cambios administrativos pueden requerir lectura con lineage en análisis más fino."
        )
        self._selected_tool_names.append("participation_decline")
        self._tool_inputs.append({"participation_decline": {"municipio_id": municipality_id, "start_year": 2019, "end_year": 2023}})
        return AskResponse(
            answer=answer,
            confidence="high",
            resultType="entity_list",
            entities=self._custom_entities(rows, "delta_pp"),
            data={"tool": "participation_decline", "operation": "compare_years", "rows": rows},
            methodology="Comparación de participación por sección entre municipales 2019 y 2023.",
            caveats=["No demuestra causalidad."],
            sources=["marts.agent_electoral_summary"],
            table=self._custom_table("Reducción de participación", rows),
            chartSpec={"type": "bar", "title": "Reducción de participación 2019-2023", "x": "section_name", "y": "delta_pp", "rows": rows},
        )

    def _winner_switch_response(self, payload: AskRequest, municipality_id: str) -> AskResponse | None:
        sql = f"""
WITH winners AS (
    SELECT
        section_id,
        section_name,
        municipio_id,
        municipio_nombre,
        election_type,
        election_year,
        election_label,
        winner_party,
        margin_pct
    FROM marts.agent_electoral_summary
    WHERE municipio_id = '{municipality_id}'
      AND winner_party IS NOT NULL
),
section_stats AS (
    SELECT
        section_id,
        MAX(section_name) AS section_name,
        MAX(municipio_id) AS municipio_id,
        MAX(municipio_nombre) AS municipio_nombre,
        COUNT(*) AS elections_checked,
        COUNT(DISTINCT winner_party) AS unique_winners,
        STRING_AGG(DISTINCT winner_party, ', ' ORDER BY winner_party) AS winner_parties,
        ROUND(AVG(margin_pct)::numeric, 2) AS average_margin_pct,
        STRING_AGG(election_type || ' ' || election_year || ': ' || winner_party || ' +' || ROUND(COALESCE(margin_pct, 0)::numeric, 1)::text || ' p.p.', ' | ' ORDER BY election_type, election_year) AS election_trace
    FROM winners
    GROUP BY section_id
),
scored AS (
    SELECT
        *,
        (unique_winners * 10 + elections_checked + COALESCE(average_margin_pct, 0) / 10.0) AS switch_score
    FROM section_stats
    WHERE unique_winners > 1
)
SELECT
    *,
    ROUND(switch_score::numeric, 2) AS value
FROM scored
ORDER BY unique_winners DESC, switch_score DESC, section_name
LIMIT 10
""".strip()
        rows = self.query_executor.execute(sql)
        if not rows:
            return None
        first = rows[0]
        ranking = "\n".join(
            f"• {row.get('section_name')} — {row.get('unique_winners')} partidos ganadores distintos: {row.get('winner_parties')}"
            for row in rows[:8]
        )
        answer = (
            f"Las secciones que más cambian de partido ganador según la elección aparecen encabezadas por {first.get('section_name')}.\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            "Qué significa\n\nEsto detecta secciones donde el comportamiento electoral cambia según el tipo de elección o el año. Es útil para identificar voto dual, voto localista o sensibilidad al contexto electoral.\n\n"
            "Cómo se ha calculado\n\nRecojo el partido ganador por sección en las elecciones disponibles, cuento cuántos ganadores distintos aparecen y ordeno las secciones con más alternancia.\n\n"
            "Interpretación útil\n\nUna sección con varios ganadores históricos puede ser más permeable al contexto electoral que una sección con un patrón estable.\n\n"
            "Cautela metodológica\n\n• No es una predicción de cambio futuro.\n"
            "• La alternancia puede depender del tipo de elección, candidaturas locales y participación."
        )
        self._selected_tool_names.append("winner_switch_by_election_type")
        self._tool_inputs.append({"winner_switch_by_election_type": {"municipio_id": municipality_id}})
        return AskResponse(
            answer=answer,
            confidence="high",
            resultType="entity_list",
            entities=self._custom_entities(rows, "unique_winners"),
            data={"tool": "winner_switch_by_election_type", "operation": "winner_switch_by_election_type", "rows": rows},
            methodology="Agrupo ganadores por sección y cuento alternancias entre elecciones disponibles.",
            caveats=["No es predicción; es histórico electoral agregado por sección."],
            sources=["marts.agent_electoral_summary"],
            table=self._custom_table("Cambio de ganador por sección", rows),
            chartSpec={"type": "bar", "title": "Secciones con cambio de ganador", "x": "section_name", "y": "unique_winners", "rows": rows},
        )

    def _electoral_evolution_response(self, payload: AskRequest, municipality_id: str) -> AskResponse | None:
        text = normalize(payload.question or "")
        party = extract_party(payload.question or "") or ("VOX" if "vox" in text else "PP")
        direction = "asc" if re.search(r"perdi[oó]|perdio|perdió", text) else "desc"
        if re.search(r"cambiaron m[aá]s entre", text):
            party_clause = ""
            value_expr = "ABS(end_vote_pct - start_vote_pct)"
            direct_metric = "cambio absoluto"
        else:
            party_clause = f"AND UPPER(canonical_party) = '{party}'"
            value_expr = "end_vote_pct - start_vote_pct"
            direct_metric = f"apoyo a {party}"
        sql = f"""
WITH base AS (
    SELECT section_id, section_name, municipio_id, municipio_nombre, canonical_party, election_year, vote_pct
    FROM marts.agent_electoral_results
    WHERE municipio_id = '{municipality_id}'
      AND election_type = 'MUNICIPALES'
      AND election_year IN (2019, 2023)
      AND vote_pct IS NOT NULL
      {party_clause}
),
pivot AS (
    SELECT
        section_id,
        MAX(section_name) AS section_name,
        MAX(municipio_id) AS municipio_id,
        MAX(municipio_nombre) AS municipio_nombre,
        COALESCE(MAX(canonical_party), 'TOTAL') AS party,
        MAX(vote_pct) FILTER (WHERE election_year = 2019) AS start_vote_pct,
        MAX(vote_pct) FILTER (WHERE election_year = 2023) AS end_vote_pct
    FROM base
    GROUP BY section_id{'' if party_clause else ', canonical_party'}
),
scored AS (
    SELECT
        *,
        ROUND((end_vote_pct - start_vote_pct)::numeric, 2) AS delta_pp,
        ROUND(({value_expr})::numeric, 2) AS value
    FROM pivot
    WHERE start_vote_pct IS NOT NULL AND end_vote_pct IS NOT NULL
)
SELECT *
FROM scored
ORDER BY value {direction.upper()}, section_name
LIMIT 10
""".strip()
        rows = self.query_executor.execute(sql)
        if not rows:
            return None
        first = rows[0]
        ranking = "\n".join(
            f"• {row.get('section_name')} — {_format_signed_decimal(row.get('delta_pp'), 1)} p.p.; "
            f"{_format_decimal(row.get('start_vote_pct'), 1)}% en 2019 → {_format_decimal(row.get('end_vote_pct'), 1)}% en 2023"
            for row in rows[:8]
        )
        asks_loss = direction == "asc"
        if asks_loss and float(first.get("delta_pp") or 0) >= 0:
            direct_sentence = (
                f"{direct_metric} no pierde apoyo entre municipales 2019 y 2023 en las secciones comparables; "
                f"la menor subida aparece en {first.get('section_name')}."
            )
        else:
            verb = "perdió más apoyo" if asks_loss else "ganó más apoyo"
            direct_sentence = f"La sección donde {direct_metric} {verb} entre municipales 2019 y 2023 es {first.get('section_name')}."
        answer = (
            f"{direct_sentence}\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            "Qué significa\n\nComparo el porcentaje de voto por sección entre dos elecciones municipales equivalentes.\n\n"
            "Cómo se ha calculado\n\nUso el porcentaje de voto de 2019 y 2023 y calculo la diferencia en puntos porcentuales.\n\n"
            "Interpretación útil\n\nPermite localizar dónde se concentró la mejora o retroceso territorial de una candidatura.\n\n"
            "Cautela metodológica\n\n• Es una comparación electoral histórica, no una predicción.\n"
            "• Los cambios pueden deberse a participación, oferta electoral o contexto local."
        )
        self._selected_tool_names.append("electoral_vote_evolution")
        self._tool_inputs.append({"electoral_vote_evolution": {"municipio_id": municipality_id, "party": None if not party_clause else party, "start_year": 2019, "end_year": 2023}})
        return AskResponse(
            answer=answer,
            confidence="high",
            resultType="entity_list",
            entities=self._custom_entities(rows, "delta_pp"),
            data={"tool": "electoral_vote_evolution", "operation": "compare_years", "rows": rows},
            methodology="Comparación de vote_pct entre municipales 2019 y 2023.",
            caveats=["No es predicción."],
            sources=["marts.agent_electoral_results"],
            table=self._custom_table("Evolución electoral 2019-2023", rows),
            chartSpec={"type": "bar", "title": "Evolución electoral 2019-2023", "x": "section_name", "y": "delta_pp", "rows": rows},
        )

    def _abstention_increase_risk_response(self, payload: AskRequest, municipality_id: str) -> AskResponse | None:
        sql = f"""
WITH electoral AS (
    SELECT
        section_id,
        MAX(section_name) AS section_name,
        MAX(municipio_id) AS municipio_id,
        MAX(municipio_nombre) AS municipio_nombre,
        MAX(abstention_pct) FILTER (WHERE election_year = 2019 AND election_type = 'MUNICIPALES') AS abstention_2019,
        MAX(abstention_pct) FILTER (WHERE election_year = 2023 AND election_type = 'MUNICIPALES') AS abstention_2023,
        MAX(participation_pct) FILTER (WHERE election_year = 2019 AND election_type = 'MUNICIPALES') AS participation_2019,
        MAX(participation_pct) FILTER (WHERE election_year = 2023 AND election_type = 'MUNICIPALES') AS participation_2023,
        MAX(margin_pct) FILTER (WHERE election_year = 2023 AND election_type = 'MUNICIPALES') AS margin_pct
    FROM marts.agent_electoral_summary
    WHERE municipio_id = '{municipality_id}'
    GROUP BY section_id
),
profile AS (
    SELECT DISTINCT ON (section_id)
        section_id,
        population_under_30_pct,
        population_over_65_pct,
        average_age
    FROM marts.agent_section_profile
    WHERE municipio_id = '{municipality_id}'
    ORDER BY section_id, year DESC
),
joined AS (
    SELECT
        electoral.*,
        profile.population_under_30_pct,
        profile.population_over_65_pct,
        COALESCE(abstention_2023 - abstention_2019, 0) AS abstention_delta_pp
    FROM electoral
    LEFT JOIN profile USING (section_id)
    WHERE abstention_2023 IS NOT NULL
),
scored AS (
    SELECT
        *,
        ROUND((
            LEAST(COALESCE(abstention_2023, 0), 65) / 65.0 * 0.45
            + GREATEST(COALESCE(abstention_delta_pp, 0), 0) / 20.0 * 0.25
            + GREATEST(0, 1 - LEAST(COALESCE(margin_pct, 30), 30) / 30.0) * 0.15
            + LEAST(COALESCE(population_under_30_pct, 0) + COALESCE(population_over_65_pct, 0), 80) / 80.0 * 0.15
        )::numeric, 4) AS value
    FROM joined
)
SELECT *
FROM scored
ORDER BY value DESC, abstention_2023 DESC, section_name
LIMIT 10
""".strip()
        rows = self.query_executor.execute(sql)
        if not rows:
            return None
        first = rows[0]
        ranking = "\n".join(
            f"• {row.get('section_name')} — índice {_format_decimal(row.get('value'), 3)}; "
            f"abstención {_format_decimal(row.get('abstention_2023'), 1)}%; cambio {_format_signed_decimal(row.get('abstention_delta_pp'), 1)} p.p."
            for row in rows[:8]
        )
        answer = (
            f"La principal señal territorial de riesgo de aumento de abstención aparece en {first.get('section_name')}.\n\n"
            f"Indicadores principales\n\n{ranking}\n\n"
            "Qué significa\n\nNo es una predicción estadística cerrada; es una señal territorial de riesgo de aumento de abstención.\n\n"
            "Cómo se ha calculado\n\nCombino abstención reciente, aumento reciente de abstención, baja competitividad relativa y una señal demográfica simple de estructura territorial.\n\n"
            "Lectura estratégica\n\nLas secciones con índice alto merecen seguimiento porque ya muestran abstención elevada o señales de desmovilización reciente.\n\n"
            "Cautela metodológica\n\n• No predice participación futura.\n"
            "• Es un proxy de alerta temprana con datos agregados por sección."
        )
        self._selected_tool_names.append("abstention_increase_risk")
        self._tool_inputs.append({"abstention_increase_risk": {"municipio_id": municipality_id}})
        return AskResponse(
            answer=answer,
            confidence="medium",
            resultType="entity_list",
            entities=self._custom_entities(rows, "value"),
            data={"tool": "abstention_increase_risk", "operation": "abstention_increase_risk", "rows": rows},
            methodology="Proxy territorial que combina abstención actual, cambio reciente, competitividad y estructura demográfica.",
            caveats=["No es una predicción estadística cerrada."],
            sources=["marts.agent_electoral_summary", "marts.agent_section_profile"],
            table=self._custom_table("Riesgo de aumento de abstención", rows),
            chartSpec={"type": "bar", "title": "Riesgo de aumento de abstención", "x": "section_name", "y": "value", "rows": rows},
        )

    def _create_agent_execution_plan(
        self,
        payload: AskRequest,
        state: ConversationState,
    ) -> AgentExecutionPlan | None:
        question = payload.question
        text = normalize(question)
        municipality_id = self.sql_generator._municipality_id(payload.activeMunicipality)
        previous_section = self._previous_section_context(state)
        last_metric = self._resolved_references.get("lastMetric") or state.lastMetric
        last_direction = self._resolved_references.get("lastDirection") or state.lastDirection

        asks_historical = bool(re.search(r"historicamente|históricamente|historico|histórico|siempre|all available", text))
        asks_party_history = bool(asks_historical and re.search(r"partido|party|vot|fuerte", text))
        asks_consistency = bool(re.search(r"siempre|always", text) and re.search(r"joven|young|envejec", text))

        if asks_consistency and (last_metric == "average_age" or re.search(r"joven|young", text)):
            if not previous_section:
                return AgentExecutionPlan(
                    userQuestion=question,
                    resolvedQuestion="Has the previously referenced section been the youngest section across all available years?",
                    task="historical_extreme_consistency",
                    requiredContext={"previousSection": True, "previousMetric": True},
                    resolvedContext={"metric": "average_age", "direction": "min"},
                    expectedAnswerType="yes_no_with_evidence",
                    renderer="historicalConsistencyRenderer",
                    confidence="low",
                )
            section_id = previous_section.sectionId
            section_name = previous_section.sectionName
            return AgentExecutionPlan(
                userQuestion=question,
                resolvedQuestion=f"Has {section_name} been the youngest section across all available years?",
                task="historical_extreme_consistency",
                requiredContext={"previousSection": True, "previousMetric": True},
                resolvedContext={
                    "sectionId": section_id,
                    "sectionName": section_name,
                    "metric": "average_age",
                    "direction": last_direction or "min",
                },
                steps=[
                    AgentPlanStep(
                        id="age_history",
                        type="sql",
                        name="average_age_extreme_by_year",
                        input={"sql": self._historical_extreme_consistency_sql(municipality_id, section_id)},
                    )
                ],
                expectedAnswerType="yes_no_with_evidence",
                renderer="historicalConsistencyRenderer",
                confidence="high",
            )

        if asks_party_history and (previous_section or re.search(r"seccion mas joven|sección mas joven|seccion más joven|sección más joven", text)):
            if not previous_section:
                return AgentExecutionPlan(
                    userQuestion=question,
                    resolvedQuestion="Which party is historically strongest in the youngest section?",
                    task="historical_party_dominance_for_section",
                    requiredContext={},
                    resolvedContext={"metric": "average_age", "direction": "min"},
                    steps=[
                        AgentPlanStep(
                            id="party_history",
                            type="sql",
                            name="party_history_for_youngest_section",
                            input={"sql": self._party_history_for_youngest_section_sql(municipality_id)},
                        )
                    ],
                    expectedAnswerType="historical_table",
                    renderer="partyHistoryRenderer",
                    confidence="high",
                )
            section_id = previous_section.sectionId
            section_name = previous_section.sectionName
            return AgentExecutionPlan(
                userQuestion=question,
                resolvedQuestion=f"Which party is historically strongest in {section_name}?",
                task="historical_party_dominance_for_section",
                requiredContext={"previousSection": True},
                resolvedContext={"sectionId": section_id, "sectionName": section_name},
                steps=[
                    AgentPlanStep(
                        id="party_history",
                        type="sql",
                        name="party_history_for_section",
                        input={"sql": self._party_history_for_section_sql(section_id)},
                    )
                ],
                expectedAnswerType="historical_table",
                renderer="partyHistoryRenderer",
                confidence="high",
            )

        if self._analytical_intent and self._analytical_intent.intent != "unknown":
            return self._single_extreme_agent_plan(question, municipality_id)

        semantic_plan = self.sql_generator.generate(
            question,
            active_municipality=municipality_id,
            resolved_references=self._resolved_references,
        )
        if semantic_plan:
            if semantic_plan.intent.startswith("municipality_population") or semantic_plan.intent in {"population_threshold_sections", "section_population_growth"}:
                return None
            if semantic_plan.expectedOutput not in {"single_value", "ranking"}:
                return None
            renderer = (
                "singleExtremeRenderer"
                if semantic_plan.expectedOutput == "single_value"
                else "rankingRenderer"
                if semantic_plan.expectedOutput == "ranking"
                else "genericTableRenderer"
            )
            metric = self._metric_from_semantic_sql(semantic_plan.sql) or semantic_plan.intent
            return AgentExecutionPlan(
                userQuestion=question,
                resolvedQuestion=question,
                task="single_extreme" if semantic_plan.expectedOutput == "single_value" else "aggregation",
                resolvedContext={"metric": metric},
                steps=[
                    AgentPlanStep(
                        id="primary",
                        type="sql",
                        name=semantic_plan.intent,
                        input={"sql": semantic_plan.sql},
                    )
                ],
                expectedAnswerType="single_value" if semantic_plan.expectedOutput == "single_value" else "ranking" if semantic_plan.expectedOutput == "ranking" else "historical_table",
                renderer=renderer,
                confidence=semantic_plan.confidence,
            )

        return None

    def _metric_from_semantic_sql(self, sql: str) -> str | None:
        for metric in (
            "population_under_30_pct",
            "population_under_30",
            "population_over_65_pct",
            "population_over_65",
            "average_age",
            "population_total",
            "population_density",
            "abstention_pct",
            "participation_pct",
            "vote_pct",
        ):
            if re.search(rf"\b{metric}\b", sql):
                return metric
        return None

    def _single_extreme_agent_plan(self, question: str, municipality_id: str) -> AgentExecutionPlan | None:
        if not self._analytical_intent:
            return None
        semantic_plan = self.sql_generator.generate(
            question,
            analytical_intent=self._analytical_intent,
            active_municipality=municipality_id,
            resolved_references=self._resolved_references,
        )
        if not semantic_plan:
            return None
        if semantic_plan.intent.startswith("municipality_population") or semantic_plan.intent == "population_threshold_sections":
            return None
        if semantic_plan.expectedOutput not in {"single_value", "ranking"}:
            return None
        metric = self._analytical_intent.metric
        direction = self._analytical_intent.direction
        asks_for_sections = bool(
            re.search(r"que secciones|qué secciones|secciones tienen|donde|zonas|areas|ranking|ordena|lista", normalize(question))
        )
        task = "single_extreme" if self._analytical_intent.intent == "single_extreme" and not asks_for_sections else "aggregation"
        renderer = "singleExtremeRenderer" if task == "single_extreme" else "rankingRenderer"
        return AgentExecutionPlan(
            userQuestion=question,
            resolvedQuestion=question,
            task=task,
            resolvedContext={
                "metric": metric,
                "direction": direction,
                "party": self._analytical_intent.filters.get("party"),
            },
            steps=[
                AgentPlanStep(
                    id="primary",
                    type="sql",
                    name=semantic_plan.intent,
                    input={"sql": semantic_plan.sql},
                )
            ],
            expectedAnswerType="single_value" if task == "single_extreme" else "ranking",
            renderer=renderer,
            confidence=self._analytical_intent.confidence,
        )

    def _validate_agent_plan(self, plan: AgentExecutionPlan) -> bool:
        if plan.requiredContext and plan.requiredContext.previousSection and not plan.resolvedContext.sectionId:
            return False
        if plan.requiredContext and plan.requiredContext.previousMetric and not plan.resolvedContext.metric:
            return False
        return bool(plan.steps)

    def _previous_section_context(self, state: ConversationState) -> ConversationSection | None:
        resolved = self._resolved_references.get("lastSection") or self._resolved_references.get("resolvedSection")
        if isinstance(resolved, dict) and resolved.get("sectionId") and resolved.get("sectionName"):
            return ConversationSection(sectionId=str(resolved["sectionId"]), sectionName=str(resolved["sectionName"]))
        if state.lastSection:
            return state.lastSection
        if state.lastSections:
            return state.lastSections[0]
        return None

    def _historical_extreme_consistency_sql(self, municipality_id: str, section_id: str) -> str:
        section_sql = section_id.replace("'", "''")
        return f"""
WITH age_rows AS (
    SELECT
        age.seccion_id AS section_id,
        COALESCE(age.label_cliente, display.label_cliente, age.seccion_id) AS section_name,
        age.anio AS year,
        age.average_age
    FROM marts.v_mapa_age_structure age
    LEFT JOIN marts.dim_seccion_display display
      ON display.seccion_id = age.seccion_id
    WHERE LEFT(age.seccion_id, 5) = '{municipality_id}'
      AND age.average_age IS NOT NULL
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY year ORDER BY average_age ASC, section_name) AS age_rank
    FROM age_rows
),
youngest AS (
    SELECT
        year,
        section_id AS youngest_section_id,
        section_name AS youngest_section_name,
        average_age AS youngest_average_age
    FROM ranked
    WHERE age_rank = 1
),
target AS (
    SELECT
        year,
        section_id AS target_section_id,
        section_name AS target_section_name,
        average_age AS target_average_age,
        age_rank AS target_rank
    FROM ranked
    WHERE section_id = '{section_sql}'
)
SELECT
    youngest.year,
    target.target_section_id,
    target.target_section_name,
    target.target_average_age,
    target.target_rank,
    youngest.youngest_section_id,
    youngest.youngest_section_name,
    youngest.youngest_average_age,
    target.target_section_id = youngest.youngest_section_id AS target_is_extreme,
    COUNT(*) OVER () AS years_checked,
    COUNT(*) FILTER (WHERE target.target_section_id = youngest.youngest_section_id) OVER () AS years_as_extreme
FROM youngest
LEFT JOIN target ON target.year = youngest.year
ORDER BY youngest.year
""".strip()

    def _party_history_for_section_sql(self, section_id: str) -> str:
        section_sql = section_id.replace("'", "''")
        return f"""
WITH party_rows AS (
    SELECT
        eb.seccion_id AS section_id,
        COALESCE(display.label_cliente, eb.seccion_id) AS section_name,
        eb.election_id,
        CONCAT(eb.tipo_eleccion_nombre, ' ', eb.anio) AS election_label,
        eb.tipo_eleccion_code AS election_type,
        eb.anio AS year,
        party_result->>'normalized_party_family' AS canonical_party,
        party_result->>'party' AS party,
        ((party_result->>'pct')::numeric * 100) AS vote_pct,
        (party_result->>'votes')::numeric AS votes,
        eb.votos_validos AS valid_votes,
        COALESCE(eb.winning_party_family, eb.winning_party) AS winner_party
    FROM marts.mv_electoral_behavior eb
    CROSS JOIN LATERAL jsonb_array_elements(eb.party_results_json) AS party_result
    LEFT JOIN marts.dim_seccion_display display
      ON display.seccion_id = eb.seccion_id
    WHERE eb.seccion_id = '{section_sql}'
      AND party_result->>'normalized_party_family' IS NOT NULL
),
party_summary AS (
    SELECT
        section_id,
        MAX(section_name) AS section_name,
        canonical_party,
        ROUND(AVG(vote_pct), 2) AS average_vote_pct,
        COUNT(*) FILTER (WHERE canonical_party = winner_party) AS first_place_count,
        SUM(votes)::bigint AS total_votes,
        COUNT(*) AS elections_included,
        MIN(year) AS first_year,
        MAX(year) AS last_year
    FROM party_rows
    GROUP BY section_id, canonical_party
)
SELECT
    section_id,
    section_name,
    canonical_party,
    average_vote_pct,
    first_place_count,
    total_votes,
    elections_included,
    first_year,
    last_year,
    RANK() OVER (ORDER BY average_vote_pct DESC, first_place_count DESC, total_votes DESC) AS historical_rank
FROM party_summary
ORDER BY historical_rank, canonical_party
LIMIT 50
""".strip()

    def _party_history_for_youngest_section_sql(self, municipality_id: str) -> str:
        municipality_sql = municipality_id.replace("'", "''")
        return f"""
WITH youngest_section AS (
    SELECT
        section_id,
        section_name,
        average_age AS youngest_average_age,
        year
    FROM marts.agent_section_profile
    WHERE municipio_id = '{municipality_sql}'
      AND average_age IS NOT NULL
      AND year = (
          SELECT MAX(year)
          FROM marts.agent_section_profile
          WHERE municipio_id = '{municipality_sql}'
            AND average_age IS NOT NULL
      )
    ORDER BY average_age ASC, section_name
    LIMIT 1
),
party_rows AS (
    SELECT
        results.section_id,
        results.section_name,
        youngest.section_name AS youngest_section_name,
        youngest.youngest_average_age,
        youngest.year AS youngest_year,
        results.election_id,
        results.election_label,
        results.election_type,
        results.election_year AS year,
        results.canonical_party,
        results.canonical_party AS party,
        results.vote_pct,
        results.votes,
        results.valid_votes,
        summary.winner_party
    FROM marts.agent_electoral_results results
    JOIN youngest_section youngest
      ON youngest.section_id = results.section_id
    LEFT JOIN marts.agent_electoral_summary summary
      ON summary.section_id = results.section_id
     AND summary.election_id = results.election_id
    WHERE results.municipio_id = '{municipality_sql}'
      AND results.canonical_party IS NOT NULL
      AND results.vote_pct IS NOT NULL
),
party_summary AS (
    SELECT
        section_id,
        MAX(section_name) AS section_name,
        MAX(youngest_section_name) AS youngest_section_name,
        MAX(youngest_average_age) AS youngest_average_age,
        MAX(youngest_year) AS youngest_year,
        canonical_party,
        ROUND(AVG(vote_pct), 2) AS average_vote_pct,
        COUNT(*) FILTER (WHERE canonical_party = winner_party) AS first_place_count,
        SUM(votes)::bigint AS total_votes,
        COUNT(*) AS elections_included,
        MIN(year) AS first_year,
        MAX(year) AS last_year
    FROM party_rows
    GROUP BY section_id, canonical_party
)
SELECT
    section_id,
    section_name,
    youngest_section_name,
    youngest_average_age,
    youngest_year,
    canonical_party,
    canonical_party AS party,
    average_vote_pct,
    first_place_count,
    total_votes,
    elections_included,
    first_year,
    last_year,
    RANK() OVER (ORDER BY average_vote_pct DESC, first_place_count DESC, total_votes DESC) AS historical_rank
FROM party_summary
ORDER BY historical_rank, canonical_party
LIMIT 50
""".strip()

    def _answer_current_question_check(
        self,
        plan: AgentExecutionPlan,
        sql_results: dict[str, list[dict[str, Any]]],
    ) -> AnswerCheck:
        rows = [row for result_rows in sql_results.values() for row in result_rows]
        if not rows:
            return AnswerCheck(passed=False, missing=["result rows"])

        fields = set().union(*(row.keys() for row in rows))
        missing: list[str] = []
        question = normalize(plan.userQuestion)

        asks_always_age = bool(re.search(r"siempre|always", question) and re.search(r"joven|young|envejec", question))
        asks_always_winner = bool(re.search(r"siempre|always", question) and re.search(r"gana|winner|fuerza", question))
        if plan.task != "historical_extreme_consistency" and asks_always_age:
            missing.append("historical_extreme_consistency task")
        if plan.task != "historical_party_dominance_for_section" and re.search(r"historicamente|históricamente", question) and re.search(r"partido|party", question):
            missing.append("historical_party_dominance_for_section task")

        if asks_always_age:
            if "year" not in fields:
                missing.append("year")
            years = {row.get("year") for row in rows if row.get("year") is not None}
            if len(years) < 2:
                missing.append("multiple years or explicit single-year limitation")
        if asks_always_winner and not {"elections_checked", "party_wins"} <= fields:
            missing.append("persistent winner fields")
        if re.search(r"historicamente|históricamente", question):
            if not {"canonical_party", "average_vote_pct", "elections_included"} <= fields:
                missing.append("party history fields")
            total_elections = max((int(row.get("elections_included") or 0) for row in rows), default=0)
            if total_elections < 2:
                missing.append("multiple elections or explicit limitation")
        if re.search(r"partido|party|votado", question) and not ({"canonical_party", "party"} & fields):
            missing.append("party fields")
        if (
            plan.task != "historical_party_dominance_for_section"
            and re.search(r"edad|joven|young|envejec", question)
            and not (
                {
                    "average_age",
                    "target_average_age",
                    "youngest_average_age",
                    "age_range_population",
                    "population_under_30",
                    "population_under_30_pct",
                    "population_over_65",
                    "population_over_65_pct",
                }
                & fields
            )
        ):
            missing.append("age fields")
        if plan.task == "single_extreme" and plan.resolvedContext.metric and plan.resolvedContext.metric not in fields:
            missing.append(plan.resolvedContext.metric)

        return AnswerCheck(passed=not missing, missing=missing)

    def _agent_check_failed_response(self, plan: AgentExecutionPlan, answer_check: AnswerCheck) -> AskResponse:
        return AskResponse(
            answer=(
                "He entendido la pregunta, pero el plan ejecutado no contiene los datos necesarios: "
                f"{', '.join(answer_check.missing)}. No voy a reutilizar una respuesta anterior porque no responde a esta consulta."
            ),
            data={"executionPlan": plan.model_dump(), "answerCheck": answer_check.model_dump()},
            methodology="Planificacion analitica con verificacion de que el resultado responde a la pregunta actual.",
            caveats=["No se ha reutilizado la respuesta anterior como respuesta final."],
            sources=[],
        )

    def _render_agent_answer(
        self,
        plan: AgentExecutionPlan,
        sql_results: dict[str, list[dict[str, Any]]],
    ) -> AskResponse:
        if plan.renderer == "historicalConsistencyRenderer":
            return self._historical_consistency_renderer(plan, sql_results["age_history"])
        if plan.renderer == "partyHistoryRenderer":
            return self._party_history_renderer(plan, sql_results["party_history"])
        if plan.renderer == "singleExtremeRenderer":
            return self._single_extreme_renderer(plan, sql_results["primary"])
        if plan.renderer == "rankingRenderer":
            return self._ranking_renderer(plan, sql_results["primary"])
        return self._generic_table_renderer(plan, [row for rows in sql_results.values() for row in rows])

    def _single_extreme_renderer(self, plan: AgentExecutionPlan, rows: list[dict[str, Any]]) -> AskResponse:
        first = rows[0]
        metric = plan.resolvedContext.metric or self._semantic_primary_metric(first)
        value = first.get(metric) if metric else None
        section_name = first.get("section_name")
        year = first.get("year")
        if metric in {"population_under_30", "population_under_30_pct"}:
            answer = self._young_population_answer(first, metric)
        elif metric in {"population_over_65", "population_over_65_pct"}:
            answer = self._senior_population_answer(first, metric)
        elif metric == "population_total":
            answer = self._population_section_answer(first, plan.resolvedContext.direction)
        elif metric == "average_age" and plan.resolvedContext.direction in {"min", "asc"}:
            answer = self._youngest_section_answer(first)
        else:
            answer = (
                f"La sección destacada es {section_name}, con {self._semantic_metric_value(metric, value)}"
                f"{f' en {year}' if year else ''}. {self._semantic_interpretation_note(metric)}"
            )
        return AskResponse(
            answer=answer,
            data={"executionPlan": plan.model_dump(), "rows": rows},
            methodology=self._metric_methodology(metric),
            caveats=[],
            sources=self._agent_sources(plan),
            table=self._rows_table("Sección destacada", rows[:1]),
            chartSpec=self._chart_spec_from_rows(
                chart_type="none",
                title="Sección destacada",
                rows=rows[:1],
                y=metric,
            ),
            suggestedFollowUps=self._population_followups() if metric == "population_total" else ["Comprobar si se mantiene en todos los años.", "Ver el histórico electoral de esa sección."],
        )

    def _ranking_renderer(self, plan: AgentExecutionPlan, rows: list[dict[str, Any]]) -> AskResponse:
        if rows and {"elections_checked", "party_wins", "always_wins"} <= set(rows[0].keys()):
            party = self._party_label(plan.userQuestion, plan.resolvedContext.party)
            return self._persistent_party_entities_response(
                party=party,
                rows=rows,
                data={"executionPlan": plan.model_dump(), "rows": rows},
                methodology=f"Cuento elecciones disponibles por sección y comparo cuántas ganó el {party}.",
                sources=self._agent_sources(plan),
                table=self._rows_table("Victorias por sección", rows[:15]),
            )
        if rows and {"age_range_population", "estimated_abstainers", "estimated_voters"} <= set(rows[0].keys()):
            first = rows[0]
            answer = (
                f"Estimo aproximadamente {_format_int(first.get('municipality_estimated_abstainers'))} abstencionistas y "
                f"{_format_int(first.get('municipality_estimated_voters'))} votantes sobre una población de "
                f"{_format_int(first.get('municipality_age_range_population'))} personas en la cohorte solicitada. "
                f"La sección con mayor abstención estimada es {first.get('section_name')}, con "
                f"{_format_int(first.get('estimated_abstainers'))} personas estimadas."
            )
            return AskResponse(
                answer=answer,
                data={"executionPlan": plan.model_dump(), "rows": rows},
                methodology="Estimo la cohorte de edad por sección y aplico la tasa de abstención observada en la elección solicitada.",
                caveats=["Es una estimación ecológica: no conocemos el voto individual por edad."],
                sources=self._agent_sources(plan),
                table=self._rows_table("Estimación por sección", rows[:15]),
            )
        metric = plan.resolvedContext.metric or self._semantic_primary_metric(rows[0]) if rows else None
        ranking_entities = self._metric_ranking_entities(metric, rows)
        if ranking_entities:
            answer, entities = ranking_entities
            return self._entity_list_response(
                answer=answer,
                entities=entities,
                data={"executionPlan": plan.model_dump(), "rows": rows},
                methodology="Ordeno las secciones por la métrica interpretada y verifico que la consulta devuelve filas con el campo solicitado.",
                sources=self._agent_sources(plan),
                table=self._rows_table("Ranking de secciones", rows[:15]),
                chartSpec=self._chart_spec_from_rows(
                    chart_type="bar",
                    title="Ranking de secciones",
                    rows=rows[:15],
                    y=metric,
                ),
            )

        return AskResponse(
            answer="He ordenado las secciones por la métrica solicitada y muestro el ranking verificado en la tabla.",
            data={"executionPlan": plan.model_dump(), "rows": rows},
            methodology="Ordeno las secciones por la métrica interpretada y verifico que la consulta devuelve filas con el campo solicitado.",
            sources=self._agent_sources(plan),
            table=self._rows_table("Ranking de secciones", rows[:15]),
            chartSpec=self._chart_spec_from_rows(
                chart_type="bar",
                title="Ranking de secciones",
                rows=rows[:15],
                y=self._semantic_primary_metric(rows[0]) if rows else None,
            ),
        )

    def _historical_consistency_renderer(self, plan: AgentExecutionPlan, rows: list[dict[str, Any]]) -> AskResponse:
        years_checked = int(rows[0].get("years_checked") or len(rows))
        years_as_extreme = int(rows[0].get("years_as_extreme") or 0)
        section_name = plan.resolvedContext.sectionName or rows[0].get("target_section_name")
        is_always = years_checked > 0 and years_as_extreme == years_checked
        exceptions = [row for row in rows if not row.get("target_is_extreme")]
        if is_always:
            answer = (
                f"Sí. He comprobado la edad media por sección en los {years_checked} años disponibles y "
                f"{section_name} fue la sección más joven en todos ellos."
            )
        else:
            exception_text = "; ".join(
                f"{row.get('year')}: {row.get('youngest_section_name')} ({_format_decimal(row.get('youngest_average_age'), 1)} años)"
                for row in exceptions[:3]
            )
            answer = (
                f"No. He comprobado la edad media por sección en los años disponibles. {section_name} fue la más joven "
                f"en {years_as_extreme} de {years_checked} años. En los otros años, la sección más joven fue: {exception_text}."
            )
        return AskResponse(
            answer=answer,
            data={"executionPlan": plan.model_dump(), "rows": rows},
            methodology="Para cada año disponible, calculo el ranking de edad media por sección y comparo si la sección referenciada ocupa el puesto 1.",
            caveats=[] if years_checked > 1 else ["Solo hay un año disponible para esta métrica."],
            sources=["marts.v_mapa_age_structure", "marts.dim_seccion_display"],
            table=self._rows_table("Sección más joven por año", rows),
            suggestedFollowUps=["Ver la evolución de edad media de esa sección.", "Compararla con la segunda sección más joven."],
        )

    def _party_history_renderer(self, plan: AgentExecutionPlan, rows: list[dict[str, Any]]) -> AskResponse:
        top = rows[0]
        section_name = plan.resolvedContext.sectionName or top.get("section_name")
        answer = (
            f"En la sección más joven identificada, {section_name}, el partido históricamente más fuerte entre las elecciones "
            f"disponibles es {top.get('canonical_party')}. Lo determino por media de voto porcentual: "
            f"{_format_decimal(top.get('average_vote_pct'), 1)}% medio en {top.get('elections_included')} elecciones, "
            f"con {top.get('first_place_count')} primeras posiciones."
        )
        return AskResponse(
            answer=answer,
            data={"executionPlan": plan.model_dump(), "rows": rows},
            methodology="Agrupo los resultados normalizados de todas las elecciones disponibles de la sección por partido canónico y ordeno por porcentaje medio, victorias y votos totales.",
            caveats=[],
            sources=["marts.mv_electoral_behavior", "marts.dim_seccion_display"],
            table=self._rows_table("Histórico de partido por sección", rows[:15]),
            suggestedFollowUps=["Ver elección por elección para ese partido.", "Comparar con otra sección joven."],
        )

    def _generic_table_renderer(self, plan: AgentExecutionPlan, rows: list[dict[str, Any]]) -> AskResponse:
        return AskResponse(
            answer="He ejecutado el plan analítico verificado y devuelvo el resultado en tabla.",
            data={"executionPlan": plan.model_dump(), "rows": rows},
            methodology="Ejecución SQL validada con comprobación de respuesta actual.",
            sources=self._agent_sources(plan),
            table=self._rows_table("Resultado analítico", rows[:15]),
        )

    def _rows_table(self, title: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not rows:
            return None
        columns = list(rows[0].keys())
        return {"title": title, "columns": columns, "rows": [[row.get(column) for column in columns] for row in rows]}

    def _party_label(self, question: str | None = None, party: str | None = None) -> str:
        resolved = party or extract_party(question or "") or self._resolved_references.get("lastParty")
        if not resolved and self._analytical_intent:
            resolved = self._analytical_intent.filters.get("party")
        return str(resolved or "PP").upper()

    def _entity_list_response(
        self,
        *,
        answer: str,
        entities: list[dict[str, Any]],
        data: dict[str, Any],
        methodology: str,
        sources: list[str],
        table: dict[str, Any] | None,
        caveats: list[str] | None = None,
        chartSpec: dict[str, Any] | None = None,
        suggestedFollowUps: list[str] | None = None,
    ) -> AskResponse:
        return AskResponse(
            answer=answer,
            resultType="entity_list",
            entities=entities,
            data=data,
            methodology=methodology,
            caveats=caveats or [],
            sources=sources,
            table=table,
            chartSpec=chartSpec,
            suggestedFollowUps=suggestedFollowUps or [],
        )

    def _chart_spec_from_rows(
        self,
        *,
        chart_type: str,
        title: str,
        rows: list[dict[str, Any]],
        x: str = "section_name",
        y: str | None = None,
    ) -> dict[str, Any]:
        return {
            "type": chart_type,
            "title": title,
            "x": x,
            "y": y,
            "rows": rows,
        }

    def _section_entity(self, row: dict[str, Any], description: str | None = None, value: str | int | float | None = None) -> dict[str, Any]:
        entity: dict[str, Any] = {
            "name": str(row.get("section_name") or row.get("sectionName") or "Sección sin nombre"),
        }
        if description:
            entity["description"] = description
        if value is not None:
            entity["value"] = value
        return entity

    def _metric_ranking_entities(self, metric: str | None, rows: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]] | None:
        if not metric or not rows:
            return None
        top_rows = rows[:5]
        if metric == "population_under_30":
            return (
                "Las secciones con más población joven son:",
                [
                    self._section_entity(row, f"{_format_int(row.get('population_under_30'))} personas menores de 30 años")
                    for row in top_rows
                ],
            )
        if metric == "population_under_30_pct":
            return (
                "Las secciones con mayor porcentaje de jóvenes son:",
                [
                    self._section_entity(row, f"{_format_decimal(row.get('population_under_30_pct'), 1)}% menores de 30")
                    for row in top_rows
                ],
            )
        if metric == "population_over_65":
            return (
                "Las secciones con más población mayor de 65 años son:",
                [
                    self._section_entity(row, f"{_format_int(row.get('population_over_65'))} personas de 65 años o más")
                    for row in top_rows
                ],
            )
        if metric == "population_over_65_pct":
            return (
                "Las secciones con mayor porcentaje de mayores de 65 son:",
                [
                    self._section_entity(row, f"{_format_decimal(row.get('population_over_65_pct'), 1)}% de población de 65 años o más")
                    for row in top_rows
                ],
            )
        if metric == "population_total":
            return (
                "Las secciones con mayor población son:",
                [
                    self._section_entity(row, f"{_format_int(row.get('population_total'))} habitantes")
                    for row in top_rows
                ],
            )
        if metric == "population_density":
            return (
                "Las secciones con mayor densidad de población son:",
                [
                    self._section_entity(row, f"{_format_decimal(row.get('population_density'), 1)} habitantes por km²")
                    for row in top_rows
                ],
            )
        if metric == "income_individual":
            return (
                "Las secciones con mayor renta individual son:",
                [
                    self._section_entity(row, f"{_format_int(row.get('income_individual'))} euros por persona")
                    for row in top_rows
                ],
            )
        if metric == "income_household":
            return (
                "Las secciones con mayor renta del hogar son:",
                [
                    self._section_entity(row, f"{_format_int(row.get('income_household'))} euros por hogar")
                    for row in top_rows
                ],
            )
        if metric == "abstention_pct":
            return (
                "Las secciones con más abstención son:",
                [
                    self._section_entity(row, f"{_format_decimal(row.get('abstention_pct'), 1)}% de abstención")
                    for row in top_rows
                ],
            )
        if metric == "participation_pct":
            return (
                "Las secciones con más participación son:",
                [
                    self._section_entity(row, f"{_format_decimal(row.get('participation_pct'), 1)}% de participación")
                    for row in top_rows
                ],
            )
        if metric == "vote_pct":
            party = top_rows[0].get("party") or self._party_label()
            return (
                f"Las secciones donde el {party} es más fuerte son:",
                [
                    self._section_entity(row, f"{_format_decimal(row.get('vote_pct'), 1)}% del voto")
                    for row in top_rows
                ],
            )
        if metric == "estimated_real_estate_value_m2":
            return (
                "Las secciones con mayor valor inmobiliario estimado son:",
                [
                    self._section_entity(row, f"{_format_int(row.get('estimated_real_estate_value_m2'))} euros/m²")
                    for row in top_rows
                ],
            )
        if metric == "residential_pressure_index":
            return (
                "Las secciones con mayor presión residencial son:",
                [
                    self._section_entity(row, f"índice {_format_decimal(row.get('residential_pressure_index'), 1)}")
                    for row in top_rows
                ],
            )
        if metric == "urban_intensity_index":
            return (
                "Las secciones con mayor intensidad construida son:",
                [
                    self._section_entity(row, f"índice {_format_decimal(row.get('urban_intensity_index'), 1)}")
                    for row in top_rows
                ],
            )
        return None

    def _persistent_party_entities_response(
        self,
        *,
        party: str,
        rows: list[dict[str, Any]],
        data: dict[str, Any],
        methodology: str,
        sources: list[str],
        table: dict[str, Any] | None,
    ) -> AskResponse:
        always = [row for row in rows if row.get("always_wins")]
        if always:
            visible = always if len(always) <= 20 else always[:10]
            answer = (
                f"El {party} gana en todas las elecciones disponibles en {len(always)} secciones de Mijas:"
                if len(always) <= 20
                else f"El {party} gana en todas las elecciones disponibles en {len(always)} secciones de Mijas. Te muestro las 10 primeras:"
            )
            entities = [
                self._section_entity(row, "primera fuerza en todas las elecciones comprobadas")
                for row in visible
            ]
            return self._entity_list_response(
                answer=answer,
                entities=entities,
                data=data,
                methodology=methodology,
                sources=sources,
                table=table,
                chartSpec=self._chart_spec_from_rows(
                    chart_type="table",
                    title=f"Secciones donde gana siempre {party}",
                    rows=visible,
                ),
            )

        closest = sorted(rows, key=lambda row: (row.get("party_wins") or 0, row.get("win_rate_pct") or 0), reverse=True)[:5]
        entities = [
            self._section_entity(
                row,
                f"gana en {_format_int(row.get('party_wins'))} de {_format_int(row.get('elections_checked'))} elecciones",
            )
            for row in closest
        ]
        return self._entity_list_response(
            answer=(
                f"No hay ninguna sección donde el {party} gane en todas las elecciones disponibles. "
                "Las secciones donde aparece con más frecuencia como primera fuerza son:"
            ),
            entities=entities,
            data=data,
            methodology=methodology,
            sources=sources,
            table=table,
            chartSpec=self._chart_spec_from_rows(
                chart_type="table",
                title=f"Secciones donde {party} se acerca más a ganar siempre",
                rows=closest,
            ),
        )

    def _agent_sources(self, plan: AgentExecutionPlan) -> list[str]:
        sql_text = " ".join(str(step.input.get("sql") or "") for step in plan.steps)
        return sorted(re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w]*\.[a-zA-Z_][\w]*)", sql_text, flags=re.IGNORECASE))

    def _remember_agent_result(
        self,
        payload: AskRequest,
        plan: AgentExecutionPlan,
        sql_results: dict[str, list[dict[str, Any]]],
    ) -> None:
        if not payload.conversationId:
            return
        state = conversation_store.get_or_create(payload.conversationId, payload.activeMunicipality or "29070")
        rows = [row for result_rows in sql_results.values() for row in result_rows]
        first = rows[0] if rows else {}
        section_id = first.get("section_id") or first.get("target_section_id") or plan.resolvedContext.sectionId
        section_name = first.get("section_name") or first.get("target_section_name") or plan.resolvedContext.sectionName

        state.lastQuestion = payload.question
        state.lastResultType = plan.task
        state.lastMetric = plan.resolvedContext.metric
        state.lastDirection = plan.resolvedContext.direction
        state.lastYear = int(first["year"]) if first.get("year") is not None else plan.resolvedContext.year
        state.lastResultRows = rows
        state.lastResult = {"task": plan.task, "rows": rows}
        state.lastOutputType = plan.expectedAnswerType
        state.analyticalContext.resultType = plan.task
        state.analyticalContext.metrics = {
            "metric": plan.resolvedContext.metric,
            "direction": plan.resolvedContext.direction,
            "renderer": plan.renderer,
        }
        if section_id and section_name:
            section = ConversationSection(sectionId=str(section_id), sectionName=str(section_name))
            state.lastSection = section
            state.lastSections = [section]
        party = plan.resolvedContext.party or extract_party(payload.question)
        if party:
            state.lastParty = party
        state.touch()

    def _ask_with_openai(self, payload: AskRequest) -> AskResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("falta instalar el paquete backend 'openai'") from exc

        client = OpenAI(
            api_key=self.settings.openai_api_key,
            timeout=self.settings.openai_timeout_seconds,
        )
        input_items: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": self._build_user_message(payload),
            }
        ]
        tool_choice: str | dict[str, str] = "required" if self._requires_tool(payload.question) else "auto"
        if self._should_use_age_abstention_tool(payload):
            tool_choice = {"type": "function", "name": "age_cohort_abstention_by_section"}
        response = client.responses.create(
            model=self.settings.openai_model,
            instructions=ASK_SOCTRACE_SYSTEM_PROMPT,
            input=input_items,
            tools=self.registry.openai_tools(),
            tool_choice=tool_choice,
            max_output_tokens=1200,
        )

        tool_results: list[dict[str, Any]] = []
        calls_seen = 0
        while True:
            function_calls = [
                item
                for item in response.output
                if getattr(item, "type", None) == "function_call"
            ]
            if not function_calls:
                return self._parse_model_response(getattr(response, "output_text", "") or "", tool_results)
            if calls_seen >= self.settings.ask_max_tool_calls:
                return self._render_from_tool_results(
                    payload.question,
                    tool_results,
                    caveat="Se ha alcanzado el limite interno de llamadas a herramientas.",
                )

            input_items += response.output
            for tool_call in function_calls:
                calls_seen += 1
                try:
                    arguments = json.loads(tool_call.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                result = self._execute_tool(tool_call.name, arguments)
                tool_results.append(
                    {
                        "name": tool_call.name,
                        "arguments": arguments,
                        "output": result,
                    }
                )
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": tool_call.call_id,
                        "output": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )

            response = client.responses.create(
                model=self.settings.openai_model,
                instructions=ASK_SOCTRACE_SYSTEM_PROMPT,
                input=input_items,
                tools=self.registry.openai_tools(),
                tool_choice="auto",
                max_output_tokens=1200,
            )

    def _ask_with_fallback(self, payload: AskRequest) -> AskResponse:
        question = payload.question
        text = normalize(question)
        municipality = payload.activeMunicipality or "29070"

        if self._should_use_age_abstention_tool(payload):
            params = self._resolve_age_abstention_params(payload)
            result = self._execute_tool("age_cohort_abstention_by_section", params)
            return self._render_from_tool_results(
                question,
                [{"name": "age_cohort_abstention_by_section", "output": result}],
            )

        if re.search(r"edad|anos|años|poblacion|personas", text) and re.search(r"\b\d{1,3}\b.*\b\d{1,3}\b", text):
            years = [int(match) for match in re.findall(r"\b(20\d{2})\b", text)]
            ages = [int(match) for match in re.findall(r"\b(\d{1,3})\b", text) if int(match) < 120]
            year = years[0] if years else payload.activeYear or 2023
            min_age, max_age = (ages[0], ages[1]) if len(ages) >= 2 else (0, ages[0])
            result = self._execute_tool(
                "demographics_age_range",
                {
                    "municipality": municipality,
                    "year": year,
                    "minAge": min(min_age, max_age),
                    "maxAge": max(min_age, max_age),
                    "gender": "all",
                    "groupBy": "municipality",
                },
            )
            return self._render_from_tool_results(question, [{"name": "demographics_age_range", "output": result}])

        if re.search(r"d\s*['’]?\s*hondt|d hondt|concejal|reparto|escano", text):
            result = self._execute_tool(
                "dhondt_calculator",
                {"municipality": municipality, "year": 2023, "seats": 25, "thresholdPct": 5},
            )
            return self._render_from_tool_results(question, [{"name": "dhondt_calculator", "output": result}])

        party = extract_party(question)
        section = extract_section_hint(question)
        if party and section and re.search(r"eleccion|elecciones|menos|mayor|mejor|peor|evolucion|porcentaje", text):
            result = self._execute_tool(
                "elections_party_section_history",
                {
                    "municipality": municipality,
                    "section": section,
                    "party": party,
                    "metric": "vote_pct",
                    "direction": extract_metric_direction(question),
                },
            )
            return self._render_from_tool_results(question, [{"name": "elections_party_section_history", "output": result}])

        if party and re.search(r"media|promedio|histor|simil|social|econom", text):
            dataset_result = self._execute_tool("available_datasets", {"municipality": municipality})
            average_result = self._execute_tool(
                "elections_party_historical_average",
                {
                    "municipality": municipality,
                    "party": party,
                    "aggregation": "section",
                    "averageType": "unweighted_pct",
                },
            )
            tool_results = [
                {"name": "available_datasets", "output": dataset_result},
                {"name": "elections_party_historical_average", "output": average_result},
            ]
            top_sections = (
                average_result.get("result", {}).get("topSections", []) if average_result.get("ok") else []
            )
            if re.search(r"simil|social|econom", text) and top_sections:
                similarity_result = self._execute_tool(
                    "socioeconomic_similarity",
                    {
                        "municipality": municipality,
                        "sectionIds": [row["sectionId"] for row in top_sections[:5]],
                        "compareAgainst": "municipality_average",
                        "indicators": ["income", "population density", "average age", "over 65", "under 30"],
                    },
                )
                tool_results.append({"name": "socioeconomic_similarity", "output": similarity_result})
            return self._render_from_tool_results(question, tool_results)

        if re.search(r"que datos tienes|datos disponibles|datasets disponibles|fuentes disponibles", text):
            result = self._execute_tool("available_datasets", {"municipality": municipality})
            return self._render_from_tool_results(
                question,
                [{"name": "available_datasets", "output": result}],
            )

        return AskResponse(
            answer=self.sql_generator.operation_interpreter.fallback_message(question),
            methodology=(
                "Intento resolver primero por catálogo semántico y operaciones analíticas aprobadas. "
                "Si no hay una métrica gobernada, la respuesta se detiene antes de inventar datos."
            ),
            caveats=[
                "Si la variable existe en soctrace, debe añadirse al catálogo semántico con sus campos y relaciones aprobadas.",
            ],
            sources=[],
            suggestedFollowUps=[
                "Preguntar explícitamente qué datos hay disponibles.",
                "Probar con población, renta, edad media, abstención, participación o voto a un partido.",
            ],
        )

    def _ask_with_semantic_sql(self, payload: AskRequest) -> AskResponse | None:
        plan = self.sql_generator.generate(
            payload.question,
            analytical_intent=self._analytical_intent,
            active_municipality=payload.activeMunicipality,
            resolved_references=self._resolved_references,
        )
        if plan is None:
            return None
        validation = self.sql_validator.validate(plan.sql)
        if not validation.ok:
            logger.warning("Ask soctrace SQL validation failed", extra={"error": validation.error, "sql": plan.sql})
            return AskResponse(
                answer="No he podido acceder temporalmente a los datos necesarios para responder la consulta.",
                methodology=plan.methodology,
                caveats=["No se ha ejecutado una consulta no validada."],
                sources=plan.sources,
                sqlDebug=plan.sql if self.settings.app_env == "development" else None,
            )
        rows = self.query_executor.execute(plan.sql)
        logger.info(
            "ask_soctrace_semantic_sql",
            extra={
                "originalQuestion": payload.question,
                "deterministicMatch": self._deterministic_match.model_dump() if self._deterministic_match else None,
                "analyticalIntent": self._analytical_intent.model_dump() if self._analytical_intent else None,
                "sqlGenerated": plan.sql if self.settings.app_env == "development" else None,
                "sqlValidation": {"ok": validation.ok, "error": validation.error},
                "executionResultCount": len(rows),
            },
        )
        self._remember_semantic_result(payload, plan, rows)
        return self._render_semantic_sql_response(plan, rows)

    def _ask_with_tools_v2(self, payload: AskRequest) -> AskResponse | None:
        if not hasattr(self, "tools_v2_executor"):
            return None
        operation = self.sql_generator.operation_interpreter.interpret(
            payload.question or "",
            municipio_id=payload.activeMunicipality or "29070",
            active_year=payload.activeYear,
            last_metric=self._resolved_references.get("lastMetric"),
            last_party=self._resolved_references.get("lastParty"),
        )
        if not operation or not operation.supported:
            return None
        tool_call = tool_call_from_operation(operation)
        if not tool_call:
            return None
        tool_name, arguments = tool_call
        self._selected_tool_names.append(tool_name)
        self._tool_inputs.append({tool_name: arguments})
        context = ToolContext(
            municipio_id=payload.activeMunicipality or "29070",
            municipio_nombre="Mijas" if (payload.activeMunicipality or "29070") == "29070" else None,
            active_year=payload.activeYear,
            conversation_id=payload.conversationId,
        )
        result = self.tools_v2_executor.execute_sync(tool_name, arguments, context)
        if result.status in {"unsupported", "error"}:
            return None
        self._remember_tool_v2_result(payload, operation, result)
        return self._render_tool_v2_response(payload, operation, result)

    def _ask_with_llm_planner(self, payload: AskRequest) -> AskResponse | None:
        if not getattr(self.settings, "ask_use_llm_planner", False):
            return None
        if not hasattr(self, "planner_loop"):
            return None
        try:
            return self._run_async(
                self.planner_loop.run(
                    question=payload.question or "",
                    conversation_id=payload.conversationId,
                    session_id=payload.session_id or payload.conversationId,
                    user_id=payload.user_id,
                    active_municipality=payload.activeMunicipality or "29070",
                    active_year=payload.activeYear,
                    active_layer=payload.activeLayer,
                    locale="es-ES",
                )
            )
        except Exception:
            logger.exception(
                "ask_llm_planner_failed",
                extra={
                    "conversation_id": payload.conversationId,
                    "question": payload.question,
                    "fallback_used": True,
                },
            )
            return None

    def _run_async(self, coroutine):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        raise RuntimeError("AskSocTraceService.ask cannot run the async planner loop inside an existing event loop.")

    def _render_tool_v2_response(self, payload: AskRequest, operation: Any, result: ToolResult) -> AskResponse:
        if result.status == "empty":
            return AskResponse(
                answer="He entendido la operación, pero no hay filas para los filtros solicitados.",
                methodology=result.methodology_plain,
                caveats=result.caveats,
                sources=result.sources,
                data={"tool": result.tool_name, "operation": result.operation, "rows": []},
            )
        answer = self._tool_v2_answer(result)
        table_rows = result.rows[:15]
        table = {
            "title": result.summary.get("value_label") or result.operation,
            "columns": list(table_rows[0].keys()) if table_rows else [],
            "rows": [[row.get(column) for column in table_rows[0].keys()] for row in table_rows] if table_rows else [],
        }
        entities = [
            self._section_entity(row, self._tool_v2_value_label(row))
            for row in result.rows
            if row.get("section_id") and row.get("section_name")
        ]
        chart_spec = result.chart_spec
        if result.tool_name == "population_growth":
            chart_spec = {
                "type": "bar",
                "title": "Crecimiento de población por zona historica",
                "x": "lineage_group_name",
                "y": "growthAbs",
                "secondaryValue": "growthPct",
                "rows": result.rows,
            }
        if result.tool_name == "age_cohort_projection" and result.rows and result.rows[0].get("target_age"):
            chart_spec = {
                "type": "bar",
                "title": "Nuevos potenciales votantes",
                "x": "section_name",
                "y": "estimated_future_age_population",
                "rows": result.rows,
            }
        if result.tool_name == "ecological_vote_profile_by_age_group":
            chart_spec = {
                "type": "bar",
                "title": "Perfil electoral estimado por grupo de edad",
                "x": "party",
                "y": "weighted_vote_pct",
                "rows": result.rows,
            }
        if result.tool_name == "electoral_viability_estimate":
            chart_spec = {
                "type": "bar" if len(result.rows) > 1 else "metric",
                "title": "Índice orientativo de viabilidad electoral",
                "x": "party",
                "y": "viability_index",
                "rows": result.rows,
            }
        if result.tool_name == "mobilizable_abstention_opportunity":
            chart_spec = {
                "type": "bar",
                "title": "Índice de abstención movilizable",
                "x": "section_name",
                "y": "score",
                "rows": result.rows,
            }
        return AskResponse(
            answer=answer,
            confidence="medium" if result.tool_name in {"cross_metric_ranking", "correlation_analysis", "ecological_vote_profile_by_age_group", "electoral_viability_estimate", "mobilizable_abstention_opportunity"} else "high",
            resultType="entity_list" if entities else "single_value",
            entities=entities,
            data={
                "tool": result.tool_name,
                "operation": result.operation,
                "rows": result.rows,
                "summary": result.summary,
                "metadata": result.metadata,
                "ctas": self._tool_v2_ctas(result),
                "explanation": result.explanation.model_dump() if result.explanation else None,
                "metric_explanations": [item.model_dump() for item in result.metric_explanations],
                "score_explanation": result.score_explanation.model_dump() if result.score_explanation else None,
            },
            methodology=result.methodology_plain,
            caveats=result.caveats,
            sources=result.sources,
            suggestedFollowUps=result.suggested_followups,
            table=table if table_rows else None,
            chartSpec=chart_spec,
        )

    def _tool_v2_ctas(self, result: ToolResult) -> list[dict[str, str]]:
        if result.tool_name == "electoral_viability_estimate":
            party = result.metadata.get("party") or (result.rows[0].get("party") if result.rows else "PP") or "PP"
            return [
                {"label": "Identificar potencial de crecimiento", "question": f"¿En qué secciones tendría más margen de crecimiento {party}?"},
                {"label": "Comparar con PSOE", "question": f"Compara la viabilidad de {party} con PSOE"},
                {"label": "Estimar reducción de abstención", "question": f"Estima el impacto de una reducción de abstención para {party}"},
            ]
        if result.tool_name == "electoral_growth_opportunity":
            party = result.metadata.get("party") or "PP"
            return [
                {"label": "Estimar votos adicionales", "question": f"¿Cuántos votos adicionales podría captar {party} en esas secciones?"},
                {"label": "Comparar con PSOE", "question": f"Comparar estas oportunidades de {party} con PSOE"},
                {"label": "Escenario alternativo", "question": f"Construir un escenario electoral alternativo para {party}"},
            ]
        if result.tool_name == "mobilizable_abstention_opportunity":
            target = result.metadata.get("target") or "general"
            if target == "general":
                return [
                    {"label": "Ver para PSOE", "question": "¿Dónde hay más abstención movilizable para PSOE?"},
                    {"label": "Ver para PP", "question": "¿Dónde hay más abstención movilizable para PP?"},
                    {"label": "Comparar con abstención total", "question": "¿Qué secciones tienen mayor abstención?"},
                    {"label": "Priorizar campaña", "question": "¿Qué zonas debería priorizar una campaña de movilización?"},
                ]
            other_party = "PP" if target != "PP" else "PSOE"
            return [
                {"label": f"Comparar con {other_party}", "question": f"¿Y para {other_party}?"},
                {"label": "Ver general", "question": "¿Dónde hay más abstención movilizable?"},
                {"label": "Priorizar candidatura", "question": "¿Qué secciones debería priorizar esta candidatura?"},
            ]
        if result.tool_name == "cross_metric_ranking":
            concept = result.metadata.get("analysis_concept")
            if concept == "demographic_polarization":
                return [
                    {"label": "Ver zonas homogéneas", "question": "¿Qué zonas son más homogéneas?"},
                    {"label": "Ver secciones más jóvenes", "question": "¿Cuál es la sección más joven?"},
                    {"label": "Ver mayores de 65", "question": "¿Dónde viven más personas mayores de 65 años?"},
                ]
            if concept == "demographic_homogeneity":
                return [
                    {"label": "Ver polarización demográfica", "question": "¿Dónde existe mayor polarización demográfica?"},
                    {"label": "Ordenar por edad media", "question": "Ordena las secciones por edad media."},
                    {"label": "Ver población total", "question": "¿Cuál es la sección con mayor población?"},
                ]
            if concept in {"housing_opportunity", "housing_revaluation_potential"}:
                return [
                    {"label": "Ver valor inmobiliario", "question": "¿Qué secciones tienen menor valor inmobiliario?"},
                    {"label": "Ver presión residencial", "question": "¿Qué secciones tienen mayor presión residencial?"},
                    {"label": "Ver intensidad edificatoria", "question": "¿Qué zonas tienen mayor intensidad edificatoria?"},
                ]
            return [
                {"label": "Ver abstención movilizable", "question": "¿Dónde hay más abstención movilizable?"},
                {"label": "Cruzar con población joven", "question": "¿Qué secciones combinan este patrón con población joven?"},
                {"label": "Ver mayor abstención", "question": "¿Qué sección tiene más abstención?"},
            ]
        return []

    def _tool_v2_answer(self, result: ToolResult) -> str:
        if not result.rows:
            return "No hay resultados para la operación solicitada."
        first = result.rows[0]
        value_label = result.summary.get("value_label") or first.get("value_label") or "valor"
        if result.tool_name == "aggregate_municipality":
            municipality = first.get("municipio_nombre") or "el municipio"
            year = first.get("year")
            if result.metadata.get("metric") == "population_total":
                return f"La población total de {municipality} es de {_format_int(first.get('value'))} habitantes en el último año disponible ({year})."
            return f"El valor municipal de {value_label} en {municipality}{f' en {year}' if year else ''} es {_format_decimal(first.get('value'), 1)}."
        if result.tool_name == "correlation_analysis":
            corr = first.get("correlation")
            return (
                f"La correlación observada entre las dos métricas es {_format_decimal(corr, 2)}. "
                "Es una lectura exploratoria por sección: no demuestra causalidad."
            )
        if result.tool_name == "persistent_winner":
            party = result.metadata.get("party") or "el partido"
            exact = [row for row in result.rows if row.get("always_wins")]
            if exact:
                return f"{party} gana en todas las elecciones disponibles en {len(exact)} secciones."
            return f"No hay secciones donde {party} gane siempre; muestro las más cercanas."
        if result.tool_name == "age_cohort_projection":
            total = first.get("municipality_total") or first.get("value")
            target_age = first.get("target_age")
            target_year = first.get("target_year")
            source_age = first.get("source_age")
            source_year = first.get("source_year")
            if target_age and target_year:
                ranking = "\n".join(
                    f"• {row.get('section_name')} — {_format_int(row.get('value'))} personas estimadas"
                    for row in result.rows[:8]
                    if row.get("section_name")
                )
                return (
                    f"Aproximadamente {_format_int(total)} personas tendrán {target_age} años en Mijas en {target_year}.\n\n"
                    f"Resultados principales\n\n{ranking}\n\n"
                    "Qué significa\n\nEsta cohorte representa a jóvenes que, por edad, podrían incorporarse al censo electoral como nuevos votantes respecto a las elecciones anteriores.\n\n"
                    f"Cómo se ha calculado\n\nTomo como referencia a quienes tenían aproximadamente {source_age} años en {source_year}; uso una quinta parte del tramo 15-19 porque la fuente disponible agrupa edades en cohortes quinquenales.\n\n"
                    "Interpretación útil\n\nSirve para localizar dónde se concentrará más población potencialmente nueva en edad de voto. El MVP estima la cohorte 2027; la comparación detallada con la cohorte nueva del ciclo municipal anterior queda como análisis posterior.\n\n"
                    "Cautela metodológica\n\n• Es elegibilidad demográfica aproximada, no predicción de participación.\n"
                    "• No estima preferencia electoral ni comportamiento individual."
                )
            return f"El total estimado es {_format_int(total)} personas. Muestro además las secciones con mayor concentración."
        if result.tool_name == "ecological_vote_profile_by_age_group":
            age_label = result.metadata.get("age_group_label") or "este grupo de edad"
            election_year = first.get("election_year") or result.metadata.get("election_year")
            parties = [str(row.get("party")) for row in result.rows[:3] if row.get("party")]
            if len(parties) >= 3:
                party_text = f"{parties[0]}, seguido de {parties[1]} y {parties[2]}"
            elif len(parties) == 2:
                party_text = f"{parties[0]}, seguido de {parties[1]}"
            else:
                party_text = parties[0] if parties else "sin partido destacado"
            lines = [
                f"• {row.get('party')}: {_format_decimal(row.get('weighted_vote_pct'), 1)}%"
                for row in result.rows[:5]
            ]
            year_text = f" ({election_year})" if election_year else ""
            return (
                "No puedo saber el voto individual por edad, porque el dataset no contiene voto individual por edad. "
                "Lo que sí puedo hacer es una estimación territorial.\n\n"
                f"Comparando las secciones con mayor peso de {age_label} con los resultados electorales disponibles{year_text}, "
                f"el partido con mayor asociación territorial en ese grupo es {party_text}.\n\n"
                "En términos prácticos, esto significa que las zonas donde ese grupo de edad pesa más tienden a mostrar "
                f"más fortaleza electoral de {parties[0] if parties else 'ese partido'}, aunque no puede afirmarse que cada persona del grupo vote a ese partido.\n\n"
                "Principales resultados:\n"
                + "\n".join(lines)
                + "\n\nMetodología: pondero el porcentaje de voto de cada partido en cada sección por el número estimado de personas "
                "del grupo de edad en esa sección."
            )
        if result.tool_name == "electoral_viability_estimate":
            formatter = getattr(self, "answer_formatter_v2", AnswerFormatterV2())
            if len(result.rows) > 1:
                return formatter.electoral_viability_comparison(result.rows)
            return formatter.electoral_viability(result.rows[0])
        if result.tool_name == "electoral_growth_opportunity":
            formatter = getattr(self, "answer_formatter_v2", AnswerFormatterV2())
            party = result.metadata.get("party") or (result.rows[0].get("party") if result.rows else None) or "el partido"
            return formatter.electoral_growth_opportunity(str(party), result.rows)
        if result.tool_name == "mobilizable_abstention_opportunity":
            return AskSocTraceService._mobilizable_abstention_answer(result)
        if result.tool_name in {"cross_metric_ranking"}:
            concept = result.metadata.get("analysis_concept")
            if concept == "demographic_polarization":
                return AskSocTraceService._demographic_polarization_answer(result)
            if concept == "demographic_homogeneity":
                return AskSocTraceService._demographic_homogeneity_answer(result)
            if concept == "housing_opportunity":
                return AskSocTraceService._housing_opportunity_answer(result)
            if concept == "housing_revaluation_potential":
                return AskSocTraceService._housing_revaluation_answer(result)
            return AskSocTraceService._cross_metric_explained_answer(result)
        if result.tool_name in {"compare_years", "population_growth"}:
            start_year = first.get("start_year")
            end_year = first.get("end_year")
            if result.tool_name == "population_growth":
                lines = []
                for row in result.rows[:5]:
                    lines.append(
                        f"• {row.get('section_name')}: {_format_signed_int(row.get('growth_abs'))} habitantes "
                        f"({_format_signed_decimal(row.get('growth_pct'), 1)}%)\n"
                        f"  Inicio: {_format_int(row.get('population_start'))} habitantes ({row.get('base_sections')})\n"
                        f"  Final: {_format_int(row.get('population_end'))} habitantes ({row.get('current_sections')})"
                    )
                return (
                    f"comparando {start_year} con {end_year}, las zonas con mayor crecimiento son:\n\n"
                    + "\n\n".join(lines)
                    + "\n\nTengo en cuenta la división administrativa de secciones censales cuando hay lineage disponible."
                )
            return f"comparando {start_year} con {end_year}, la zona destacada es {first.get('section_name')}, con una variación de {_format_decimal(first.get('value'), 1)} en {value_label}."
        if result.tool_name == "filter_sections":
            threshold = (result.metadata.get("condition") or {}).get("value")
            if threshold:
                return f"Actualmente hay {len(result.rows)} secciones que superan los {_format_int(threshold)} habitantes."
            return f"He encontrado {len(result.rows)} secciones que cumplen los filtros solicitados."
        if first.get("section_name"):
            metric = result.metadata.get("metric")
            if metric == "population_total":
                if result.metadata.get("order") == "asc":
                    return f"La sección menos poblada de Mijas es {first.get('section_name')}, con aproximadamente {_format_int(first.get('value'))} habitantes."
                return f"La sección más poblada de Mijas es {first.get('section_name')}, con aproximadamente {_format_int(first.get('value'))} habitantes."
            if metric == "population_under_30":
                return f"La sección con más población joven es {first.get('section_name')}, con {_format_int(first.get('value'))} personas menores de 30 años."
            if metric == "population_under_30_pct":
                ranking = "\n".join(
                    f"• {row.get('section_name')} — {_format_decimal(row.get('value'), 1)}%"
                    for row in result.rows[:10]
                )
                return (
                    f"La sección con mayor porcentaje de población menor de 30 años es {first.get('section_name')}, con {_format_decimal(first.get('value'), 1)}%.\n\n"
                    f"Resultados principales\n\n{ranking}\n\n"
                    "Qué significa\n\nAquí uso valor relativo: el porcentaje de menores de 30 sobre la población total de cada sección.\n\n"
                    "Cómo se ha calculado\n\nDivido la población menor de 30 años entre la población total de la sección y ordeno de mayor a menor porcentaje.\n\n"
                    "Cautela metodológica\n\nUna sección puede tener alto porcentaje joven aunque no sea la que tiene más jóvenes en número absoluto."
                )
            if metric == "population_over_65":
                return f"La sección con más personas mayores de 65 años es {first.get('section_name')}, con {_format_int(first.get('value'))} personas."
            if metric == "population_over_65_pct":
                ranking = "\n".join(
                    f"• {row.get('section_name')} — {_format_decimal(row.get('value'), 1)}%"
                    for row in result.rows[:10]
                )
                return (
                    f"La sección con mayor porcentaje de población mayor de 65 años es {first.get('section_name')}, con {_format_decimal(first.get('value'), 1)}%.\n\n"
                    f"Resultados principales\n\n{ranking}\n\n"
                    "Qué significa\n\nAquí uso valor relativo: el peso de las personas de 65 años o más sobre la población total de cada sección.\n\n"
                    "Cómo se ha calculado\n\nDivido la población de 65 años o más entre la población total de la sección y ordeno de mayor a menor porcentaje.\n\n"
                    "Interpretación útil\n\nSirve para detectar secciones con estructura más envejecida aunque no tengan el mayor número absoluto de personas mayores.\n\n"
                    "Cautela metodológica\n\nNo mide pensionistas reales; usa edad 65+ como proxy demográfico."
                )
            if metric == "population_under_18":
                return f"La sección con más menores de 18 años es {first.get('section_name')}, con {_format_int(first.get('value'))} personas."
            if metric == "population_under_18_pct":
                return f"La sección con mayor porcentaje de menores de 18 años es {first.get('section_name')}, con {_format_decimal(first.get('value'), 1)}%."
            if metric == "margin_pct":
                ranking = "\n".join(
                    f"• {row.get('section_name')} — margen {_format_decimal(row.get('value'), 1)} p.p.; "
                    f"{row.get('winner_party')} frente a {row.get('second_party')}; elección {row.get('year')}"
                    for row in result.rows[:10]
                )
                if result.metadata.get("order") == "asc":
                    direct = f"La sección más disputada es {first.get('section_name')}, con un margen de {_format_decimal(first.get('value'), 1)} puntos."
                    meaning = "Una sección disputada es aquella donde la diferencia entre primera y segunda fuerza es baja."
                else:
                    direct = f"La sección con mayor margen de victoria es {first.get('section_name')}, con {_format_decimal(first.get('value'), 1)} puntos."
                    meaning = "Un margen alto indica una victoria territorialmente más holgada de la primera fuerza."
                return (
                    f"{direct}\n\n"
                    f"Resultados principales\n\n{ranking}\n\n"
                    f"Qué significa\n\n{meaning}\n\n"
                    "Cómo se ha calculado\n\nUso la última elección municipal disponible y calculo la diferencia en puntos porcentuales entre el partido ganador y el segundo partido.\n\n"
                    "Interpretación útil\n\nLas secciones con margen bajo son más competitivas y pueden ser relevantes para priorización electoral.\n\n"
                    "Cautela metodológica\n\nLa competitividad electoral depende de la elección analizada; el patrón puede cambiar en autonómicas, generales o europeas."
                )
            if metric == "winner_party":
                return f"En {first.get('section_name')}, el partido ganador registrado es {first.get('value')}."
            if metric == "average_age":
                rows = result.rows
                ranking = "\n".join(
                    f"• {row.get('section_name')}: {_format_decimal(row.get('value'), 1)} años"
                    for row in rows[:10]
                )
                if result.metadata.get("order") == "asc":
                    return (
                        "Ordeno las secciones de menor a mayor edad media.\n\n"
                        f"La sección más joven es {first.get('section_name')}, con una edad media de {_format_decimal(first.get('value'), 1)} años.\n\n"
                        f"Resultados principales\n\n{ranking}\n\n"
                        "Qué significa\n\nUna edad media más baja indica una estructura demográfica más joven, no necesariamente más población joven en términos absolutos.\n\n"
                        "Cómo se ha calculado\n\nOrdeno las secciones por la edad media estimada de la población residente en el último año disponible.\n\n"
                        "Interpretación útil\n\nSirve para detectar zonas con perfil de edad más joven o más envejecido y priorizar análisis de servicios, vivienda o comunicación territorial.\n\n"
                        "Cautela metodológica\n\nLa edad media resume la estructura de edad de cada sección; conviene complementarla con porcentajes de menores de 30 y mayores de 65 para interpretar mejor cada zona."
                    )
                return (
                    f"La sección más envejecida es {first.get('section_name')}, con una edad media de {_format_decimal(first.get('value'), 1)} años.\n\n"
                    f"Resultados principales\n\n{ranking}\n\n"
                    "Una edad media alta apunta a mayor peso relativo de población adulta y mayor, pero no sustituye al análisis por cohortes."
                )
            if metric == "market_price_estimated_m2":
                return AskSocTraceService._housing_value_rank_answer(result, lower=result.metadata.get("order") == "asc")
            if metric == "residential_pressure_index":
                return AskSocTraceService._residential_pressure_answer(result)
            if metric in {"building_intensity", "built_footprint", "parcel_density"}:
                return AskSocTraceService._built_environment_answer(result)
            return f"La sección destacada es {first.get('section_name')}, con {_format_decimal(first.get('value'), 1)} en {value_label}."
        return "He ejecutado la herramienta analítica y devuelvo el resultado en tabla."

    @staticmethod
    def _rank_lines(rows: list[dict[str, Any]], value_key: str = "value", suffix: str = "") -> str:
        return "\n".join(
            f"• {row.get('section_name')}: {_format_decimal(row.get(value_key), 3)}{suffix}"
            for row in rows[:10]
        )

    @staticmethod
    def _demographic_polarization_answer(result: ToolResult) -> str:
        rows = result.rows or []
        first = rows[0]
        ranking = "\n".join(
            f"• {row.get('section_name')}: índice {_format_decimal(row.get('value'), 3)}; "
            f"jóvenes {_format_decimal(row.get('value_1'), 1)}%; mayores {_format_decimal(row.get('value_2'), 1)}%"
            for row in rows[:10]
        )
        return (
            f"La mayor polarización demográfica aparece en {first.get('section_name')}.\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            "Qué significa\n\nLa mayor polarización demográfica aparece en las secciones donde conviven, con mayor intensidad, población joven y población mayor. No significa conflicto social.\n\n"
            "Cómo se ha calculado\n\nEl índice combina el peso relativo de menores de 30 años y mayores de 65 años. Cuanto más alto es, más marcada es esa convivencia de extremos de edad.\n\n"
            "Interpretación útil\n\nEn soctrace se interpreta como una estructura de edad más dual: secciones con peso relevante tanto de jóvenes como de mayores.\n\n"
            "Cautela metodológica\n\nEs un proxy territorial comparativo. No mide relaciones sociales, convivencia real ni conflicto; solo resume la estructura de edad disponible por sección."
        )

    @staticmethod
    def _demographic_homogeneity_answer(result: ToolResult) -> str:
        rows = result.rows or []
        first = rows[0]
        ranking = "\n".join(
            f"• {row.get('section_name')}: índice {_format_decimal(row.get('value'), 3)}; "
            f"jóvenes {_format_decimal(row.get('value_1'), 1)}%; mayores {_format_decimal(row.get('value_2'), 1)}%"
            for row in rows[:10]
        )
        return (
            f"Las zonas más homogéneas aparecen encabezadas por {first.get('section_name')}.\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            "Qué significa\n\nHomogénea significa que la sección tiene una estructura de edad menos extrema y más concentrada en tramos centrales.\n\n"
            "Cómo se ha calculado\n\nOrdeno primero las secciones con menor peso relativo simultáneo de población joven y población mayor.\n\n"
            "Interpretación útil\n\nUn valor alto en este ranking apunta a menos dualidad en los extremos de edad.\n\n"
            "Cautela metodológica\n\nEs una lectura demográfica simplificada. Para una homogeneidad más fina haría falta distribución completa por cohortes y un índice de dispersión por edades."
        )

    @staticmethod
    def _housing_opportunity_answer(result: ToolResult) -> str:
        rows = result.rows or []
        first = rows[0]
        ranking = "\n".join(
            f"• {row.get('section_name')}: índice {_format_decimal(row.get('value'), 3)}; "
            f"relación mercado/catastro {_format_decimal(row.get('value_1'), 2)}; presión {_format_decimal(row.get('value_2'), 1)}"
            for row in rows[:10]
        )
        return (
            f"Las mejores oportunidades inmobiliarias aparecen encabezadas por {first.get('section_name')}.\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            "Qué significa\n\nLas mejores oportunidades inmobiliarias son las zonas donde el valor estimado, la presión residencial y la relación mercado/catastro sugieren mayor margen de recorrido.\n\n"
            "Cómo se ha calculado\n\nPara el MVP priorizo zonas con menor relación mercado/catastro y menor presión residencial relativa.\n\n"
            "Interpretación útil\n\nLa idea es buscar margen comparativo, no zonas ya sobrecalentadas. No significa recomendación de compra automática, sino una lectura territorial comparativa.\n\n"
            "Cautela metodológica\n\nEs un proxy con datos agregados por sección. No sustituye tasación, micro-localización, estado del inmueble, normativa urbanística ni análisis financiero."
        )

    @staticmethod
    def _housing_revaluation_answer(result: ToolResult) -> str:
        rows = result.rows or []
        first = rows[0]
        ranking = "\n".join(
            f"• {row.get('section_name')}: índice {_format_decimal(row.get('value'), 3)}; "
            f"relación mercado/catastro {_format_decimal(row.get('value_1'), 2)}; intensidad {_format_decimal(row.get('value_2'), 1)}"
            for row in rows[:10]
        )
        return (
            f"El mayor potencial comparativo de revalorización aparece en {first.get('section_name')}.\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            "Qué significa\n\nPara el MVP lo interpreto como zonas con margen relativo de valor y señales de intensidad territorial, evitando leerlo como predicción de precio.\n\n"
            "Cómo se ha calculado\n\nCombino menor relación mercado/catastro con mayor intensidad edificatoria relativa.\n\n"
            "Interpretación útil\n\nUn índice alto puede señalar zonas con recorrido territorial, pero no una garantía de rentabilidad.\n\n"
            "Cautela metodológica\n\nNo incorpora transacciones recientes, licencias futuras ni estado de activos concretos. Es una comparación territorial orientativa."
        )

    @staticmethod
    def _housing_value_rank_answer(result: ToolResult, *, lower: bool) -> str:
        rows = result.rows or []
        first = rows[0]
        ranking = "\n".join(
            f"• {row.get('section_name')}: {_format_decimal(row.get('value'), 0)} €/m²"
            for row in rows[:10]
        )
        adjective = "menor" if lower else "mayor"
        return (
            f"La sección con {adjective} valor inmobiliario estimado es {first.get('section_name')}.\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            "Interpretación útil\n\nEl valor estimado por metro cuadrado permite comparar presión y atractivo inmobiliario entre secciones.\n\n"
            "Cautela metodológica\n\nEs una estimación territorial agregada, no una tasación de inmuebles concretos."
        )

    @staticmethod
    def _residential_pressure_answer(result: ToolResult) -> str:
        rows = result.rows or []
        first = rows[0]
        ranking = AskSocTraceService._rank_lines(rows)
        return (
            f"El mercado más tensionado aparece en {first.get('section_name')}.\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            "Interpretación útil\n\nLa presión residencial resume señales territoriales de tensión inmobiliaria y uso residencial.\n\n"
            "Cautela metodológica\n\nEs un índice comparativo por sección; no describe cada inmueble ni sustituye análisis urbanístico detallado."
        )

    @staticmethod
    def _built_environment_answer(result: ToolResult) -> str:
        rows = result.rows or []
        first = rows[0]
        ranking = AskSocTraceService._rank_lines(rows)
        return (
            f"La sección destacada es {first.get('section_name')}.\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            "Interpretación útil\n\nEstos indicadores describen intensidad física y estructura del suelo construido por sección.\n\n"
            "Cautela metodológica\n\nSon datos agregados y deben cruzarse con planeamiento y uso real del suelo para decisiones concretas."
        )

    @staticmethod
    def _cross_metric_explained_answer(result: ToolResult) -> str:
        rows = result.rows or []
        first = rows[0] if rows else {}
        metric_explanations = result.metric_explanations or []
        score = result.score_explanation
        variables = metric_explanations[:2]
        variable_label = " y ".join(item.label.lower() for item in variables) if variables else "los factores solicitados"
        score_name = score.score_name if score else "Índice combinado"
        direct = f"La sección que mejor combina {variable_label} es {first.get('section_name')}."
        variable_lines = "\n".join(
            f"• {item.label}: {item.plain_definition} {item.interpretation}"
            for item in variables
        )
        value_text = ""
        if first.get("value") is not None:
            value_text = f" En este caso, {_format_decimal(first.get('value'), 3)} indica una combinación {'muy alta' if float(first.get('value') or 0) >= 0.8 else 'alta' if float(first.get('value') or 0) >= 0.6 else 'media'}."
        ranking = "\n".join(
            f"• {row.get('section_name')} — {_format_decimal(row.get('value'), 3)}"
            for row in rows[:6]
        )
        explanation = result.explanation
        practical = explanation.practical_use if explanation else "Sirve para priorizar decisiones territoriales según varios criterios a la vez."
        caveats = explanation.caveats if explanation else ["No demuestra causalidad.", "No mide comportamientos individuales; es una lectura territorial por sección."]
        return (
            f"{direct}\n\n"
            f"Resultados principales\n\n{ranking}\n\n"
            f"Qué significa\n\nPara responder, combino dos factores:\n{variable_lines}\n\n"
            f"Cómo se ha calculado\n\n{score_name} va de {score.scale if score else '0 a 1'}. "
            f"{score.plain_definition if score else 'Cuanto más alto es, más se concentran los factores en la misma sección.'}{value_text}\n\n"
            f"Interpretación útil\n\n{practical}\n\n"
            f"Cautela metodológica\n\n" + "\n".join(f"• {item}" for item in caveats) + "\n\n"
            "Preguntas relacionadas\n\n"
            "• ¿Dónde hay más abstención movilizable?\n"
            "• ¿Qué zonas debería priorizar una campaña de movilización?\n"
            "• ¿Qué secciones tienen mayor abstención?"
        )

    @staticmethod
    def _mobilizable_abstention_answer(result: ToolResult) -> str:
        rows = result.rows or []
        target = result.metadata.get("target") or "general"
        target_text = " en términos generales" if target == "general" else f" para {target}"
        if target == "general":
            related = (
                "• ¿Qué secciones tienen mayor abstención?\n"
                "• ¿Qué zonas debería priorizar una campaña de movilización?\n"
                "• ¿Dónde hay más abstencionistas potenciales?"
            )
        else:
            related = (
                "• ¿Y para PP?\n"
                "• ¿Y para PSOE?\n"
                "• ¿Qué secciones debería priorizar esta candidatura?"
            )
        direct = (
            f"La zona con mayor abstención movilizable{target_text} es {rows[0].get('section_name')}."
            if rows
            else "No encuentro secciones con datos suficientes para estimar abstención movilizable."
        )
        ranking = "\n".join(
            f"• {row.get('section_name')} — índice {_format_decimal(row.get('score') or row.get('value'), 3)}; "
            f"abstención {_format_decimal(row.get('abstention_pct'), 1)}%; "
            f"margen {_format_decimal(row.get('margin_pct'), 1)} puntos; "
            f"abstencionistas estimados {_format_int(row.get('estimated_abstainers'))}"
            for row in rows[:6]
        )
        return (
            f"{direct}\n\n"
            "Indicadores principales\n\n"
            f"{ranking}\n\n"
            "Qué significa\n\n"
            "Las zonas con más abstención movilizable no son simplemente las que tienen más abstención. "
            "Son secciones donde la abstención tiene más valor estratégico porque coincide con peso electoral, competitividad y, si hay contexto político, afinidad territorial.\n\n"
            "Cómo se ha calculado\n\n"
            "soctrace combina cuatro factores:\n"
            "• Nivel de abstención.\n"
            "• Peso electoral de la sección, usando censo o población como aproximación.\n"
            "• Competitividad electoral, dando más peso a márgenes estrechos.\n"
            "• Afinidad territorial con el bloque o partido cuando la conversación lo permite.\n\n"
            "Lectura estratégica\n\n"
            "El índice va de 0 a 1. Cuanto más cerca está de 1, mayor es la oportunidad territorial de movilización. "
            "Una sección con índice alto combina abstención relevante, tamaño suficiente y una contienda competitiva, por lo que puede ser prioritaria para una campaña de activación.\n\n"
            "Cautela metodológica\n\n"
            "• No es una predicción individual de voto.\n"
            "• No demuestra que las personas abstencionistas vayan a votar a un partido concreto.\n"
            "• Es una lectura estratégica por sección, útil para priorizar territorio.\n\n"
            "Preguntas relacionadas\n\n"
            f"{related}"
        )

    def _tool_v2_value_label(self, row: dict[str, Any]) -> str:
        value = row.get("value")
        label = row.get("value_label") or "valor"
        if isinstance(value, (int, float)):
            return f"{_format_decimal(value, 1)} {label}"
        return str(label)

    def _remember_tool_v2_result(self, payload: AskRequest, operation: Any, result: ToolResult) -> None:
        if not payload.conversationId:
            return
        state = conversation_store.get_or_create(payload.conversationId, payload.activeMunicipality or "29070")
        rows = result.rows
        first = rows[0] if rows else {}
        state.lastQuestion = payload.question
        state.lastTool = result.tool_name
        state.last_tool_name = result.tool_name
        state.last_operation = result.operation
        state.lastResultType = result.operation
        state.lastMetric = operation.metric or result.metadata.get("metric")
        state.lastYear = self._int_or_none(first.get("year")) or payload.activeYear
        state.last_start_year = self._int_or_none(first.get("start_year"))
        state.last_end_year = self._int_or_none(first.get("end_year"))
        state.lastParty = operation.party or result.metadata.get("party")
        state.last_party = state.lastParty
        state.last_election = {"type": operation.election_type, "year": operation.election_year} if operation.election_type or operation.election_year else None
        state.lastResultRows = rows
        state.last_rows = rows
        state.lastResult = {"tool": result.tool_name, "rows": rows, "summary": result.summary, "metadata": result.metadata}
        state.last_chart_spec = result.chart_spec
        state.lastMetrics = result.summary
        state.lastOutputType = result.operation
        state.lastSections = [
            ConversationSection(
                sectionId=str(row["section_id"]),
                sectionName=str(row["section_name"]),
                value=row.get("value") if isinstance(row.get("value"), (int, float)) else None,
                valueLabel=str(row.get("value_label") or ""),
            )
            for row in rows
            if row.get("section_id") and row.get("section_name")
        ]
        if state.lastSections:
            state.lastSection = state.lastSections[0]
        state.analyticalContext.resultType = result.operation
        state.analyticalContext.metrics = {"metric": state.lastMetric, **result.summary}
        state.touch()

    def _render_semantic_sql_response(self, plan: SemanticPlan, rows: list[dict[str, Any]]) -> AskResponse:
        if not rows:
            return AskResponse(
                answer="He entendido la operación, pero la consulta no devolvió filas para los filtros solicitados.",
                methodology=plan.methodology,
                caveats=["No se han inferido datos ausentes."],
                sources=plan.sources,
                sqlDebug=plan.sql if self.settings.app_env == "development" else None,
            )

        first = rows[0]
        caveats = list(plan.caveats or [])
        answer = self._semantic_answer(plan, rows)
        table_rows = rows[:15]
        table = {
            "title": self._semantic_table_title(plan),
            "columns": list(table_rows[0].keys()) if table_rows else [],
            "rows": [[row.get(column) for column in table_rows[0].keys()] for row in table_rows] if table_rows else [],
        }
        data = {
            "intent": plan.intent,
            "rows": rows,
            "totals": self._semantic_totals(plan, first),
        }
        entity_result = self._semantic_entity_result(plan, rows, data, table)
        if entity_result:
            return entity_result
        return AskResponse(
            answer=answer,
            data=data,
            methodology=plan.methodology,
            caveats=caveats,
            sources=plan.sources,
            suggestedFollowUps=self._semantic_followups(plan),
            table=table,
            chartSpec={**plan.chartSpec, "rows": rows} if plan.chartSpec else None,
            sqlDebug=plan.sql if self.settings.app_env == "development" else None,
        )

    def _semantic_answer(self, plan: SemanticPlan, rows: list[dict[str, Any]]) -> str:
        first = rows[0]
        if plan.intent == "age_cohort_turnout_estimation":
            population = first.get("municipality_age_range_population")
            abstainers = first.get("municipality_estimated_abstainers")
            voters = first.get("municipality_estimated_voters")
            voter_pct = 100 * float(voters) / float(population) if population else 0
            abstention_pct = 100 * float(abstainers) / float(population) if population else 0
            return (
                f"Estimo aproximadamente {_format_int(abstainers)} abstencionistas y {_format_int(voters)} votantes "
                f"sobre una población de {_format_int(population)} personas en la cohorte solicitada. "
                f"Esto equivale a una participación estimada del {_format_decimal(voter_pct, 1)}% "
                f"y una abstención estimada del {_format_decimal(abstention_pct, 1)}%."
            )
        if plan.intent == "future_age_cohort_projection":
            total = first.get("municipality_estimated_future_age_population")
            source_year = first.get("source_year")
            source_age = first.get("source_age")
            target_year = first.get("target_year")
            target_age = first.get("target_age")
            top_lines = "\n".join(
                f"• {row.get('section_name')} — {_format_int(row.get('estimated_future_age_population'))} personas"
                for row in rows[:5]
            )
            return (
                f"Aproximadamente {_format_int(total)} personas tendrán {target_age} años en Mijas en {target_year}.\n\n"
                f"La estimación se calcula tomando como referencia a quienes tenían aproximadamente {source_age} años en {source_year}. "
                "Como soctrace dispone aquí de cohortes quinquenales, uso una quinta parte del tramo 15-19 como aproximación.\n\n"
                f"Las secciones con más nuevos potenciales votantes serían:\n\n{top_lines}\n\n"
                f"Desde el punto de vista electoral, esta cohorte es relevante porque previsiblemente podrá votar por primera vez "
                f"en las elecciones municipales de mayo de {target_year}. Este cálculo no predice participación electoral; solo estima "
                "cuántas personas alcanzarían la edad legal de voto."
            )
        if plan.intent == "party_always_wins_by_section":
            party = self._party_label(plan.question)
            always = [row for row in rows if row.get("always_wins")]
            if always:
                return f"El {party} gana en todas las elecciones disponibles en {len(always)} secciones de Mijas:"
            return (
                f"No hay ninguna sección donde el {party} gane en todas las elecciones disponibles. "
                "Las secciones donde aparece con más frecuencia como primera fuerza son:"
            )
        if plan.intent == "young_population_high_abstention_sections":
            top = rows[0]
            return (
                f"La sección que más combina población joven y abstención alta es {top.get('section_name')}, "
                f"con score {_format_decimal(top.get('young_abstention_score'), 2)}."
            )
        if plan.intent == "historical_party_average_by_section":
            top = rows[0]
            return (
                f"La sección con mayor media histórica de voto del partido consultado es {top.get('section_name')}, "
                f"con {_format_decimal(top.get('average_vote_pct'), 1)}%."
            )
        if plan.intent == "high_income_high_party_vote_sections":
            top = rows[0]
            return (
                f"La sección que más combina renta alta y voto alto al partido consultado es {top.get('section_name')}, "
                f"con renta individual de {_format_int(top.get('individual_income'))} euros y "
                f"{_format_decimal(top.get('vote_pct'), 1)}% de voto."
            )
        if plan.intent == "previous_sections_winner_count":
            matching = first.get("matching_sections")
            total = first.get("total_sections")
            return f"En {matching} de las {total} secciones anteriores ganó el partido consultado en 2023."
        if plan.intent == "municipality_population_total":
            municipality = first.get("municipio_nombre") or "Mijas"
            year = first.get("year")
            growth = first.get("growth_pct_since_first_year")
            first_year = first.get("first_year")
            trend_sentence = (
                f"La evolución reciente muestra un crecimiento del {_format_decimal(growth, 1)}% desde {first_year}."
                if growth is not None and first_year and first_year != year
                else "Uso el último año disponible del dataset para evitar fijar un año desactualizado."
            )
            return (
                f"La población total estimada de {municipality} es de {_format_int(first.get('population_total'))} habitantes "
                f"según el último año disponible del dataset ({year}).\n\n"
                f"{trend_sentence}\n\n"
                "El cálculo se realiza agregando la población residente registrada en todas las secciones censales del municipio."
            )
        if plan.intent == "municipality_population_trend":
            return self._population_trend_answer(rows)
        if plan.intent == "section_population_growth":
            return self._population_growth_answer(rows, plan)
        if plan.intent == "population_threshold_sections":
            threshold = self.sql_generator._extract_population_threshold(normalize(plan.question)) or 0
            year = first.get("year")
            section_word = "sección" if len(rows) == 1 else "secciones"
            return (
                f"Actualmente hay {len(rows)} {section_word} que supera{'n' if len(rows) != 1 else ''} los {_format_int(threshold)} habitantes en {year}.\n\n"
                "Estas zonas concentran una parte importante de la población del municipio y suelen tener un peso territorial relevante.\n\n"
                "El cálculo compara la población residente de cada sección censal en el último año disponible."
            )
        if plan.intent in {"section_metric_extreme", "section_metric_ranking"}:
            metric = self._semantic_primary_metric(first)
            section_name = first.get("section_name")
            value = first.get(metric) if metric else None
            year = first.get("year")
            if plan.expectedOutput == "single_value" and metric:
                if metric in {"population_under_30", "population_under_30_pct"}:
                    return self._young_population_answer(first, metric)
                if metric in {"population_over_65", "population_over_65_pct"}:
                    return self._senior_population_answer(first, metric)
                if metric == "average_age":
                    return self._youngest_section_answer(first)
                if metric == "population_total":
                    direction = "min" if re.search(r"menor|menos|menos poblada|least", normalize(plan.question)) else "max"
                    return self._population_section_answer(first, direction)
                return (
                    f"La sección destacada es {section_name}, con {self._semantic_metric_value(metric, value)}"
                    f"{f' en {year}' if year else ''}. {self._semantic_interpretation_note(metric)}"
                )
            return "He ordenado las secciones por la métrica solicitada y muestro el ranking en la tabla."
        return "He ejecutado una consulta analítica segura y devuelvo el resultado en tabla."

    def _semantic_entity_result(
        self,
        plan: SemanticPlan,
        rows: list[dict[str, Any]],
        data: dict[str, Any],
        table: dict[str, Any] | None,
    ) -> AskResponse | None:
        if plan.intent == "party_always_wins_by_section":
            party = self._party_label(plan.question)
            return self._persistent_party_entities_response(
                party=party,
                rows=rows,
                data=data,
                methodology=plan.methodology,
                sources=plan.sources,
                table=table,
            )
        if plan.intent == "population_threshold_sections":
            entities = [
                self._section_entity(row, f"{_format_int(row.get('population_total'))} habitantes")
                for row in rows
            ]
            return self._entity_list_response(
                answer=self._semantic_answer(plan, rows),
                entities=entities,
                data=data,
                methodology=plan.methodology,
                sources=plan.sources,
                table=table,
                caveats=plan.caveats or [],
                chartSpec=self._chart_spec_from_rows(
                    chart_type="bar",
                    title=self._semantic_table_title(plan),
                    rows=rows[:15],
                    y="population_total",
                ),
                suggestedFollowUps=self._semantic_followups(plan),
            )
        if plan.intent == "section_population_growth":
            entities = [
                self._section_entity(
                    row,
                    f"{_format_signed_int(self._row_growth_abs(row))} habitantes ({_format_signed_decimal(self._row_growth_pct(row), 1)}%)",
                )
                for row in rows
            ]
            return self._entity_list_response(
                answer=self._semantic_answer(plan, rows),
                entities=entities,
                data=data,
                methodology=plan.methodology,
                sources=plan.sources,
                table=table,
                caveats=plan.caveats or [],
                chartSpec={**(plan.chartSpec or {}), "rows": rows},
                suggestedFollowUps=self._semantic_followups(plan),
            )
        if plan.intent == "future_age_cohort_projection":
            entities = [
                self._section_entity(row, f"{_format_int(row.get('estimated_future_age_population'))} personas")
                for row in rows
            ]
            return self._entity_list_response(
                answer=self._semantic_answer(plan, rows),
                entities=entities,
                data=data,
                methodology=plan.methodology,
                sources=plan.sources,
                table=table,
                caveats=plan.caveats or [],
                chartSpec={**(plan.chartSpec or {}), "rows": rows},
                suggestedFollowUps=self._semantic_followups(plan),
            )
        if plan.intent == "section_metric_ranking":
            metric = self._semantic_primary_metric(rows[0]) if rows else None
            ranking_entities = self._metric_ranking_entities(metric, rows)
            if ranking_entities:
                answer, entities = ranking_entities
                return self._entity_list_response(
                    answer=answer,
                    entities=entities,
                    data=data,
                    methodology=plan.methodology,
                    sources=plan.sources,
                    table=table,
                    caveats=plan.caveats or [],
                    chartSpec=self._chart_spec_from_rows(
                        chart_type="bar",
                        title=self._semantic_table_title(plan),
                        rows=rows[:15],
                        y=metric,
                    ),
                )
        return None

    def _semantic_primary_metric(self, row: dict[str, Any]) -> str | None:
        for metric in (
            "average_age",
            "population_under_30",
            "population_under_30_pct",
            "population_over_65",
            "population_over_65_pct",
            "population_total",
            "income_individual",
            "income_household",
            "abstention_pct",
            "participation_pct",
            "vote_pct",
            "winning_party_pct",
            "estimated_future_age_population",
        ):
            if metric in row:
                return metric
        return None

    def _semantic_metric_value(self, metric: str, value: Any) -> str:
        if metric == "average_age":
            return f"una edad media de {_format_decimal(value, 1)} años"
        if metric in {"population_under_30", "population_over_65"}:
            return f"{_format_int(value)} personas"
        if metric in {"population_under_30_pct", "population_over_65_pct"}:
            return f"{_format_decimal(value, 1)}%"
        if metric == "population_total":
            return f"{_format_int(value)} habitantes"
        if metric in {"income_individual", "income_household"}:
            return f"una renta de {_format_int(value)} euros"
        if metric in {"abstention_pct", "participation_pct", "vote_pct", "winning_party_pct"}:
            return f"{_format_decimal(value, 1)}%"
        return str(value)

    def _semantic_interpretation_note(self, metric: str) -> str:
        notes = {
            "average_age": "Interpreto “más joven/más envejecida” como menor o mayor edad media.",
            "population_under_30": "Interpreto “jóvenes” como número absoluto de personas menores de 30 años.",
            "population_under_30_pct": "Interpreto “en porcentaje” como peso de menores de 30 sobre la población total de la sección.",
            "population_over_65": "Interpreto “mayores” como número absoluto de personas de 65 años o más.",
            "population_over_65_pct": "Interpreto “porcentaje de mayores” como peso de 65+ sobre la población total de la sección.",
            "population_total": "Interpreto población como habitantes totales de la sección.",
            "income_individual": "Interpreto renta como renta media individual.",
            "income_household": "Interpreto renta del hogar como renta media por hogar.",
            "abstention_pct": "Interpreto abstención como porcentaje de censo que no emitió voto.",
            "participation_pct": "Interpreto participación como porcentaje de censo que emitió voto.",
            "vote_pct": "Interpreto fuerza del partido como porcentaje de voto válido.",
        }
        return notes.get(metric, "")

    def _metric_methodology(self, metric: str | None) -> str:
        if metric in {"population_under_30", "population_under_30_pct", "population_over_65", "population_over_65_pct"}:
            return (
                "Agrupo la población por tramos de edad en cada sección. "
                "Para porcentajes divido el grupo de edad entre la población total de la misma sección."
            )
        if metric == "population_total":
            return "Agrego la población residente por sección censal y comparo los resultados del último año disponible."
        return "Ordeno las secciones por la métrica interpretada y selecciono el extremo solicitado con SQL validado."

    def _young_population_answer(self, row: dict[str, Any], metric: str) -> str:
        year = row.get("year")
        if metric == "population_under_30_pct":
            return (
                f"La sección con mayor porcentaje de jóvenes es {row.get('section_name')}, con "
                f"{_format_decimal(row.get('population_under_30_pct'), 1)}% de población menor de 30 años"
                f"{f' en {year}' if year else ''}. En términos absolutos son {_format_int(row.get('population_under_30'))} personas. "
                "Aquí cambio la métrica a peso relativo: no tiene por qué coincidir con la sección con más jóvenes en número absoluto."
            )
        return (
            f"La sección con mayor número absoluto de jóvenes es {row.get('section_name')}, con "
            f"{_format_int(row.get('population_under_30'))} personas menores de 30 años"
            f"{f' en {year}' if year else ''}. "
            "Esto es distinto de “sección más joven”, que se refiere a la edad media más baja."
        )

    def _youngest_section_answer(self, row: dict[str, Any]) -> str:
        year = row.get("year")
        return (
            f"La sección más joven de Mijas es {row.get('section_name')}, con una edad media de "
            f"{_format_decimal(row.get('average_age'), 1)} años"
            f"{f' en {year}' if year else ''}."
        )

    def _population_section_answer(self, row: dict[str, Any], direction: str | None) -> str:
        year = row.get("year")
        section_name = row.get("section_name")
        population = _format_int(row.get("population_total"))
        is_minimum = direction in {"min", "asc"} or re.search(r"menor|menos|least", normalize(str(self._analytical_intent.direction if self._analytical_intent else "")))
        if is_minimum:
            direct = (
                f"La sección menos poblada de Mijas es {section_name}, con aproximadamente {population} habitantes"
                f"{f' en {year}' if year else ''}."
            )
            interpretation = "Se trata de una de las áreas con menor peso demográfico dentro del municipio."
        else:
            direct = (
                f"La sección más poblada de Mijas es {section_name}, con aproximadamente {population} habitantes "
                f"en el último año disponible"
                f"{f' ({year})' if year else ''}."
            )
            interpretation = (
                "Esto indica que se trata de una de las zonas con mayor peso demográfico del municipio y, previsiblemente, "
                "una de las áreas con mayor demanda potencial de servicios públicos, movilidad y equipamientos."
            )
        scientific_basis = (
            "El cálculo se realiza agregando la población residente registrada en cada sección censal y comparando los resultados "
            "para el año seleccionado."
        )
        return f"{direct}\n\n{interpretation}\n\n{scientific_basis}"

    def _population_trend_answer(self, rows: list[dict[str, Any]]) -> str:
        first = rows[0]
        last = rows[-1]
        start_population = float(first.get("population_total") or 0)
        end_population = float(last.get("population_total") or 0)
        growth_pct = ((end_population - start_population) / start_population * 100) if start_population else 0
        evolution = "\n".join(
            f"{row.get('year')} → {_format_int(row.get('population_total'))} habitantes"
            for row in rows
        )
        trend = "crecimiento" if growth_pct > 0 else "descenso" if growth_pct < 0 else "estabilidad"
        return (
            f"La población de Mijas ha pasado de {_format_int(first.get('population_total'))} habitantes en {first.get('year')} "
            f"a {_format_int(last.get('population_total'))} habitantes en {last.get('year')}.\n\n"
            f"Esto supone un {trend} de {_format_decimal(abs(growth_pct), 1)}%.\n\n"
            f"La evolución ha sido:\n\n{evolution}\n\n"
            "La tendencia general observada es de crecimiento demográfico sostenido en la serie disponible.\n\n"
            "El cálculo suma la población de todas las secciones censales para cada año y compara el primer y último dato de la serie."
        )

    def _population_growth_answer(self, rows: list[dict[str, Any]], plan: SemanticPlan) -> str:
        first = rows[0]
        start_year = first.get("start_year")
        end_year = first.get("end_year")
        ranks_by_pct = bool(plan.chartSpec and plan.chartSpec.get("y") in {"growth_pct", "growthPct"})
        lost_population = any(float(self._row_growth_abs(row) or 0) < 0 for row in rows)
        if lost_population and normalize(plan.question).find("perd") >= 0:
            intro = (
                "Las zonas que más población han perdido son las zonas historicas con mayor descenso de habitantes "
                "entre el primer y el último año comparado."
            )
        elif ranks_by_pct:
            intro = (
                "Las zonas que más han crecido en porcentaje son las zonas historicas con mayor aumento relativo respecto "
                "a su población inicial."
            )
        else:
            intro = (
                "Las zonas que más han crecido en Mijas son las que más población han ganado "
                "entre el primer y el último año disponible del dataset."
            )
        split_rows = [row for row in rows if row.get("includes_split")]
        split_note = (
            "En este cálculo tengo en cuenta la división administrativa de secciones censales. "
            "Por ejemplo, la actual Sección 37 no existía al inicio de la serie y procede de la antigua zona de la Sección 25. "
            "Por eso, para medir el crecimiento real de esa zona, comparo la población de la Sección 25 al inicio "
            "con la suma de las Secciones 25 y 37 al final."
            if split_rows
            else "En este cálculo puedo tener en cuenta la división administrativa de secciones censales cuando la línea histórica está disponible."
        )
        bullet_lines: list[str] = []
        for row in rows[:5]:
            before = row.get("base_sections") or "secciones base disponibles"
            after = row.get("current_sections") or "secciones actuales disponibles"
            bullet_lines.append(
                f"• {row.get('lineage_group_name') or row.get('section_name')}: {_format_signed_int(self._row_growth_abs(row))} habitantes "
                f"({_format_signed_decimal(self._row_growth_pct(row), 1)}%)\n"
                f"  Inicio: {_format_int(row.get('population_start'))} habitantes ({before})\n"
                f"  Final: {_format_int(row.get('population_end'))} habitantes ({after})"
            )
        bullets = "\n\n".join(bullet_lines)
        if lost_population and normalize(plan.question).find("perd") >= 0:
            interpretation = (
                "Este resultado mide pérdida demográfica absoluta: prioriza las zonas que más habitantes han perdido, "
                "no necesariamente las que más han caído en proporción a su tamaño inicial."
            )
        elif ranks_by_pct:
            interpretation = (
                "Este resultado mide crecimiento demográfico relativo: destaca secciones que han crecido mucho en proporción a su tamaño inicial."
            )
        else:
            interpretation = (
                "Este resultado mide crecimiento demográfico absoluto. Es decir, prioriza las zonas que más habitantes han incorporado, "
                "no necesariamente las que más han crecido en proporción a su tamaño inicial."
            )
        return (
            f"{intro}\n\n"
            f"{split_note}\n\n"
            f"En Mijas, comparando {start_year} con {end_year}, las zonas con mayor crecimiento son:\n\n"
            f"{bullets}\n\n"
            f"{interpretation}\n\n"
            "Este enfoque evita interpretar como caída o aparición artificial lo que en realidad es una división administrativa de una zona que ha crecido."
        )

    def _row_growth_abs(self, row: dict[str, Any]) -> Any:
        return row.get("growth_abs", row.get("growthAbs"))

    def _row_growth_pct(self, row: dict[str, Any]) -> Any:
        return row.get("growth_pct", row.get("growthPct"))

    def _population_followups(self) -> list[str]:
        return [
            "¿Qué secciones tienen mayor densidad de población?",
            "¿Qué zonas han crecido más?",
            "¿Qué secciones concentran más población joven?",
        ]

    def _population_followups_text(self) -> str:
        return "También puedes preguntarme:\n\n" + "\n".join(f"• {question}" for question in self._population_followups())

    def _senior_population_answer(self, row: dict[str, Any], metric: str) -> str:
        year = row.get("year")
        if metric == "population_over_65_pct":
            return (
                f"La sección con mayor porcentaje de mayores de 65 es {row.get('section_name')}, con "
                f"{_format_decimal(row.get('population_over_65_pct'), 1)}% de su población"
                f"{f' en {year}' if year else ''}. En términos absolutos son {_format_int(row.get('population_over_65'))} personas."
            )
        return (
            f"La sección con mayor número de mayores de 65 es {row.get('section_name')}, con "
            f"{_format_int(row.get('population_over_65'))} personas"
            f"{f' en {year}' if year else ''}."
        )

    def _semantic_table_title(self, plan: SemanticPlan) -> str:
        return {
            "age_cohort_turnout_estimation": "Estimación por sección",
            "party_always_wins_by_section": "Victorias por sección",
            "young_population_high_abstention_sections": "Población joven y abstención",
            "historical_party_average_by_section": "Media histórica por sección",
            "high_income_high_party_vote_sections": "Renta y voto por sección",
            "previous_sections_winner_count": "Ganador en secciones anteriores",
            "future_age_cohort_projection": "Nuevos potenciales votantes por sección",
            "section_metric_extreme": "Sección destacada",
            "section_metric_ranking": "Ranking de secciones",
            "municipality_population_total": "Población municipal",
            "municipality_population_trend": "Evolución de población",
            "population_threshold_sections": "Secciones por umbral de población",
            "section_population_growth": "Crecimiento de población por zona historica",
        }.get(plan.intent, "Resultado analítico")

    def _semantic_totals(self, plan: SemanticPlan, first: dict[str, Any]) -> dict[str, Any]:
        if plan.intent == "age_cohort_turnout_estimation":
            return {
                "ageRangePopulation": first.get("municipality_age_range_population"),
                "estimatedAbstainers": first.get("municipality_estimated_abstainers"),
                "estimatedVoters": first.get("municipality_estimated_voters"),
            }
        if plan.intent == "previous_sections_winner_count":
            return {
                "matchingSections": first.get("matching_sections"),
                "totalSections": first.get("total_sections"),
            }
        if plan.intent == "municipality_population_total":
            return {
                "populationTotal": first.get("population_total"),
                "year": first.get("year"),
                "growthPctSinceFirstYear": first.get("growth_pct_since_first_year"),
            }
        if plan.intent == "section_population_growth":
            return {
                "startYear": first.get("start_year"),
                "endYear": first.get("end_year"),
            }
        if plan.intent == "future_age_cohort_projection":
            return {
                "estimatedFutureAgePopulation": first.get("municipality_estimated_future_age_population"),
                "sourceYear": first.get("source_year"),
                "sourceAge": first.get("source_age"),
                "targetYear": first.get("target_year"),
                "targetAge": first.get("target_age"),
            }
        return {}

    def _semantic_followups(self, plan: SemanticPlan) -> list[str]:
        if plan.intent == "future_age_cohort_projection":
            return [
                "¿Qué secciones tendrán más nuevos votantes en 2027?",
                "¿Qué zonas concentran más jóvenes que podrán votar por primera vez en 2027?",
                "¿Dónde viven más menores de 18 años?",
            ]
        if plan.intent.startswith("municipality_population") or plan.intent in {"population_threshold_sections", "section_population_growth"}:
            return self._population_followups()
        if plan.intent in {"section_metric_extreme", "section_metric_ranking"} and "population_total" in plan.sql:
            return self._population_followups()
        if plan.intent == "age_cohort_turnout_estimation":
            return ["Ver ranking por sección.", "Compararlo con renta o edad media.", "Repetir para otra cohorte."]
        if plan.intent.endswith("sections"):
            return ["Comparar estas secciones con renta.", "Ver quién ganó en esas secciones."]
        return ["Comparar con otra variable territorial.", "Ver tabla por sección."]

    def _remember_semantic_result(self, payload: AskRequest, plan: SemanticPlan, rows: list[dict[str, Any]]) -> None:
        if not payload.conversationId:
            return
        state = conversation_store.get_or_create(payload.conversationId, payload.activeMunicipality or "29070")
        state.lastQuestion = payload.question
        state.lastSql = plan.sql
        state.lastResultRows = rows
        state.lastResult = {"intent": plan.intent, "rows": rows}
        state.lastResultType = plan.intent
        state.lastOutputType = plan.expectedOutput
        first = rows[0] if rows else {}
        metric = self._semantic_primary_metric(first) if first else None
        state.lastMetric = metric
        state.lastYear = int(first["year"]) if first.get("year") is not None else payload.activeYear
        state.lastMetrics = self._semantic_totals(plan, rows[0]) if rows else {}
        state.analyticalContext.resultType = plan.intent
        state.analyticalContext.metrics = {"metric": metric, **state.lastMetrics}
        state.lastSections = [
            ConversationSection(sectionId=str(row["section_id"]), sectionName=str(row["section_name"]))
            for row in rows
            if row.get("section_id") and row.get("section_name")
        ]
        if state.lastSections:
            state.lastSection = state.lastSections[0]
        if plan.intent == "age_cohort_turnout_estimation":
            age_range = self.sql_generator._extract_age_range(payload.question)
            if age_range:
                from app.ask.conversation.conversation_state import ActiveElection, AgeRange

                state.lastAgeRange = AgeRange(minAge=age_range[0], maxAge=age_range[1])
                state.activeElection = ActiveElection(
                    type=self.sql_generator._extract_election_type(payload.question) or "municipales",
                    year=self.sql_generator._extract_year(payload.question) or 2023,
                )
        party = extract_party(payload.question)
        if party:
            state.lastParty = party
        state.touch()

    def _execute_plan(self, payload: AskRequest, plan: ExecutionPlan) -> AskResponse:
        tool_results: list[dict[str, Any]] = []
        for step in plan.steps:
            if step.action != "call_tool" or not step.toolName:
                continue
            result = self._execute_tool(step.toolName, step.toolInput)
            tool_results.append({"name": step.toolName, "arguments": step.toolInput, "output": result})
        return self._render_plan_response(payload.question, plan, tool_results)

    def _render_plan_response(
        self,
        question: str,
        plan: ExecutionPlan,
        tool_results: list[dict[str, Any]],
    ) -> AskResponse:
        if not tool_results or not tool_results[-1].get("output", {}).get("ok"):
            return AskResponse(
                answer="He recuperado el contexto anterior, pero no he podido ejecutar la herramienta necesaria con datos suficientes.",
                data={"executionPlan": plan.model_dump(), "tools": tool_results},
                methodology="Resolucion de referencias conversacionales seguida de ejecucion de herramientas aprobadas.",
                caveats=["No se han inventado datos para completar la respuesta."],
                sources=[],
                suggestedFollowUps=["Repetir la pregunta indicando año, proceso electoral o secciones concretas."],
            )

        primary = tool_results[-1]
        data = primary["output"]["result"]
        sources = [primary["name"]]
        if isinstance(data, dict):
            sources.extend(data.get("sources", []))

        if plan.intent == "count_winner_party_in_previous_sections":
            party = extract_party(question) or plan.resolvedReferences.get("lastParty") or "PP"
            sections = data.get("sections", [])
            matching = [
                section
                for section in sections
                if normalize(str(section.get("winningParty"))) == normalize(party)
                or normalize(str(section.get("winningPartyLabel"))) == normalize(party)
            ]
            total = len(sections)
            return AskResponse(
                answer=(
                    f"En {len(matching)} de las {total} secciones recuperadas de la consulta anterior, "
                    f"{party} fue la fuerza mas votada en {data.get('year', 2023)}."
                ),
                data={
                    "executionPlan": plan.model_dump(),
                    "sections": sections,
                    "matchingSections": matching,
                    "count": len(matching),
                    "totalSections": total,
                },
                methodology=(
                    "He resuelto 'esas secciones' usando el conjunto de secciones guardado en la conversacion y "
                    "despues he consultado el partido ganador observado por seccion."
                ),
                caveats=["El conteo usa el conjunto de secciones de la consulta anterior, no todas las secciones de Mijas."],
                sources=sources,
                suggestedFollowUps=["Listar solo las secciones donde gano PP.", "Compararlas con renta media y edad media."],
                table={
                    "title": "Ganador por sección recuperada",
                    "columns": ["sectionName", "winningParty", "winningVotePct"],
                    "rows": [
                        [
                            section.get("sectionName"),
                            section.get("winningParty"),
                            section.get("winningVotePct"),
                        ]
                        for section in sections
                    ],
                },
                chartSpec={"type": "bar", "x": "sectionName", "y": "winningVotePct", "groupBy": "winningParty"},
            )

        if plan.intent in {
            "average_income_previous_sections",
            "average_age_previous_sections",
            "compare_previous_sections_with_mijas",
        }:
            rows = data.get("sections", [])
            income_avg = _average([row.get("individual_income") for row in rows])
            household_avg = _average([row.get("household_income") for row in rows])
            age_avg = _average([row.get("average_age") for row in rows])
            municipality_income = _first_number(rows, "municipality_individual_income")
            municipality_household = _first_number(rows, "municipality_household_income")
            municipality_age = _first_number(rows, "municipality_average_age")
            if plan.intent == "average_income_previous_sections":
                answer = (
                    f"La renta media individual de esas {len(rows)} secciones es aproximadamente "
                    f"{_format_int(income_avg)} euros. La renta media del hogar es aproximadamente "
                    f"{_format_int(household_avg)} euros."
                )
            elif plan.intent == "average_age_previous_sections":
                answer = (
                    f"La edad media de esas {len(rows)} secciones es aproximadamente "
                    f"{_format_decimal(age_avg, 1)} años."
                )
            else:
                answer = (
                    f"Comparadas con el conjunto de Mijas, esas {len(rows)} secciones tienen una renta individual media de "
                    f"{_format_int(income_avg)} euros frente a {_format_int(municipality_income)} euros municipales, "
                    f"y una edad media de {_format_decimal(age_avg, 1)} años frente a "
                    f"{_format_decimal(municipality_age, 1)} años en Mijas."
                )
            return AskResponse(
                answer=answer,
                data={
                    "executionPlan": plan.model_dump(),
                    "sections": rows,
                    "metrics": {
                        "selectedIndividualIncome": income_avg,
                        "municipalityIndividualIncome": municipality_income,
                        "selectedHouseholdIncome": household_avg,
                        "municipalityHouseholdIncome": municipality_household,
                        "selectedAverageAge": age_avg,
                        "municipalityAverageAge": municipality_age,
                    },
                },
                methodology=(
                    "He resuelto la referencia a las secciones anteriores y he calculado medias sobre los indicadores "
                    "socioeconomicos y demograficos disponibles para esas secciones."
                ),
                caveats=[
                    "La comparacion es descriptiva y depende de la cobertura disponible por seccion.",
                    "No se han cambiado las secciones de referencia entre turnos.",
                ],
                sources=sources + ["marts.v_income_level_layer", "marts.v_mapa_age_structure_2023"],
                suggestedFollowUps=["Ver la tabla por seccion.", "Comparar estas secciones con el resto del municipio."],
            )

        return self._render_from_tool_results(question, tool_results)

    def _render_from_tool_results(
        self,
        question: str,
        tool_results: list[dict[str, Any]],
        caveat: str | None = None,
    ) -> AskResponse:
        successful = [item for item in tool_results if item.get("output", {}).get("ok")]
        sources = sorted({item["name"] for item in successful})
        caveats = [caveat] if caveat else []
        if not successful:
            return AskResponse(
                answer="He entendido la pregunta, pero no hay datos disponibles para ese año/rango/proceso electoral en el dataset actual.",
                data=tool_results,
                methodology="Se intento resolver la pregunta mediante herramientas aprobadas de soctrace.",
                caveats=caveats,
                sources=sources,
                suggestedFollowUps=["Concretar año, seccion, partido o indicador disponible."],
            )

        primary = successful[-1]
        name = primary["name"]
        data = primary["output"]["result"]
        if name == "age_cohort_abstention_by_section":
            totals = data["totals"]
            rows = data.get("rows", [])
            top = rows[0] if rows else None
            age_range = data["ageRange"]
            age_label = age_range.get("label") or (
                f"{age_range['minAge']} años o más"
                if age_range.get("maxAge") is None
                else f"{age_range['minAge']} a {age_range['maxAge']} años"
            )
            if top:
                voter_rate = (
                    100 * float(totals["estimatedVoters"]) / float(totals["ageRangePopulation"])
                    if totals.get("ageRangePopulation")
                    else 0
                )
                rate_sentence = (
                    f"Eso equivale a una participación estimada del {_format_decimal(voter_rate, 1)}% para la cohorte, "
                    f"y una abstención estimada del {_format_decimal(totals.get('weightedAbstentionRatePct'), 1)}%. "
                )
                answer = (
                    f"He estimado la participación y la abstención de la población de {age_label} "
                    f"en las {data['electionType']} de {data['year']} por sección. "
                    f"{rate_sentence}"
                    f"La sección con mayor abstención estimada en este rango es {top['sectionName']}, "
                    f"con aproximadamente {_format_int(top['estimatedAbstainers'])} personas de esa cohorte que no habrían votado. "
                    f"En total, la estimación suma {_format_int(totals['estimatedAbstainers'])} abstencionistas y "
                    f"{_format_int(totals['estimatedVoters'])} votantes estimados sobre {_format_int(totals['ageRangePopulation'])} personas."
                )
            else:
                answer = (
                    "He entendido la pregunta, pero no hay datos por sección suficientes para cruzar población por edad "
                    "y abstención electoral en el año/proceso solicitado."
                )
            return AskResponse(
                answer=answer,
                data=data,
                methodology=(
                    "Primero estimo cuántas personas del rango de edad solicitado hay en cada sección usando core.poblacion_edad. "
                    "Cuando el rango corta cohortes quinquenales, prorrateo proporcionalmente. Después aplico a esa cohorte "
                    "la tasa de abstención observada en la misma sección para el proceso electoral seleccionado."
                ),
                caveats=caveats + data.get("caveats", []),
                sources=sources + data.get("sources", []),
                suggestedFollowUps=[
                    "Comparar el mismo cálculo con otra cohorte de edad.",
                    "Ver solo las secciones con más abstención estimada.",
                    "Compararlo con renta o densidad por sección.",
                ],
            )
        if name == "demographics_age_range":
            method = "exacto" if data["method"] == "exact" else "estimado desde cohortes quinquenales"
            return AskResponse(
                answer=(
                    f"En {data['municipality']} habia {int(data['total']):,} personas de {data['ageRange']} años "
                    f"en {data['year']} segun el calculo {method}."
                ).replace(",", "."),
                data=data,
                methodology="Suma de core.poblacion_edad por cohortes de edad y genero; si el rango corta una cohorte, se prorratea.",
                caveats=caveats + (["El resultado es estimado porque el rango solicitado corta cohortes de edad."] if data["method"] != "exact" else []),
                sources=sources + ["core.poblacion_edad"],
                suggestedFollowUps=["Ver el mismo rango por seccion.", "Compararlo con 2021-2025."],
            )
        if name == "elections_party_section_history":
            selected = data.get("selected")
            if not selected:
                return AskResponse(
                    answer="He identificado la seccion y el partido, pero no hay resultados normalizados suficientes.",
                    data=data,
                    methodology="Filtro de resultados electorales normalizados por seccion y partido canonico.",
                    caveats=caveats,
                    sources=sources + ["core.resultados_seccion"],
                    suggestedFollowUps=["Probar con otro partido o seccion."],
                )
            return AskResponse(
                answer=(
                    f"En {data['sectionName']}, el resultado seleccionado de {data['party']} es "
                    f"{float(selected['vote_pct']):.1f}% en {_election_label(selected)}."
                ),
                data=data,
                methodology="Comparacion de porcentaje de voto valido por eleccion disponible, no de votos absolutos.",
                caveats=caveats + ["Solo se incluyen elecciones cargadas y normalizadas en soctrace."],
                sources=sources + ["core.resultados_seccion", "core.election", "core.candidatura_alias"],
                suggestedFollowUps=["Comparar con PSOE y VOX en la misma seccion."],
            )
        if name == "elections_party_historical_average":
            top = data.get("topSections", [None])[0]
            if not top:
                return AskResponse(
                    answer=f"No encuentro datos normalizados suficientes para calcular la media historica de {data.get('party', 'ese partido')}.",
                    data=data,
                    methodology="Media simple de porcentaje de voto valido por seccion y eleccion.",
                    caveats=caveats,
                    sources=sources,
                    suggestedFollowUps=["Consultar available_datasets para ver procesos cargados."],
                )
            return AskResponse(
                answer=(
                    f"La seccion con mayor media historica de {data['party']} es {top['sectionName']}, "
                    f"con {top['averageVotePct']:.1f}% en {top['electionsIncluded']} elecciones incluidas."
                ),
                data={"tools": tool_results},
                methodology="Media simple no ponderada de porcentajes por seccion y eleccion; la similitud, si aparece, compara las secciones lideres con medias municipales.",
                caveats=caveats + ["Resultado descriptivo, no causal.", "Solo usa procesos disponibles en soctrace."],
                sources=sources + ["core.resultados_seccion", "marts.dim_seccion_display"],
                suggestedFollowUps=["Pedir la tabla completa por seccion.", "Comparar con otro partido."],
            )
        if name == "socioeconomic_similarity":
            sections = data.get("sections", [])
            return AskResponse(
                answer=(
                    f"He comparado {len(sections)} secciones lideres con la media municipal usando indicadores disponibles. "
                    "La lectura es descriptiva: renta, edad, densidad y entorno construido pueden coincidir parcialmente, pero no prueban causalidad electoral."
                ),
                data={"tools": tool_results},
                methodology="Primero se obtiene el ranking historico electoral y despues se cruzan las secciones con indicadores socioeconomicos aprobados.",
                caveats=caveats + ["La similitud no implica causalidad.", "Hay indicadores con cobertura parcial por seccion."],
                sources=sources + ["marts.v_income_level_layer", "marts.v_population_layer", "marts.v_land_built_environment"],
                suggestedFollowUps=["Separar costa, urbanizaciones e interior.", "Comparar con el perfil del PSOE."],
            )
        if name == "dhondt_calculator":
            return AskResponse(
                answer=f"El reparto D'Hondt municipal calculado para {data['year']} asigna concejales asi: {data['seats']}.",
                data=data,
                methodology="Cocientes D'Hondt sobre votos observados, 25 concejales y umbral del 5%.",
                caveats=caveats + ["No hay un numero fijo de votos por concejal; depende del ranking de cocientes."],
                sources=sources + ["core.resultados_seccion"],
                suggestedFollowUps=["Mostrar cocientes de un partido concreto."],
            )
        return AskResponse(
            answer="He localizado los datasets disponibles para orientar la consulta, pero necesito una variable mas concreta para calcular una respuesta numerica segura.",
            data=data,
            methodology="Consulta de disponibilidad de datasets aprobados.",
            caveats=caveats,
            sources=sources,
            suggestedFollowUps=["Preguntar por edad, partido, seccion, renta o reparto D'Hondt."],
        )

    def _parse_model_response(self, text: str, tool_results: list[dict[str, Any]]) -> AskResponse:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self._render_from_tool_results("", tool_results, caveat="El renderizador LLM no devolvio JSON valido.")
        return AskResponse(
            answer=str(parsed.get("answer") or ""),
            data=parsed.get("data"),
            methodology=parsed.get("methodology"),
            caveats=list(parsed.get("caveats") or []),
            sources=list(parsed.get("sources") or []),
            suggestedFollowUps=list(parsed.get("suggestedFollowUps") or []),
        )

    def _build_user_message(self, payload: AskRequest) -> str:
        context = {
            "question": payload.question,
            "conversationId": payload.conversationId,
            "activeMunicipality": payload.activeMunicipality or "29070",
            "activeYear": payload.activeYear,
            "activeLayer": payload.activeLayer,
            "lastResolvedEntities": self._conversation_state(payload.conversationId),
            "resolvedReferences": self._resolved_references,
            "executionPlan": self._execution_plan.model_dump() if self._execution_plan else None,
        }
        return json.dumps(context, ensure_ascii=False)

    def _requires_tool(self, question: str) -> bool:
        text = normalize(question)
        return bool(
            re.search(
                r"\d|cuant|ranking|compar|porcentaje|total|media|promedio|tendencia|forecast|prevision|d hondt|d['’]?hondt|renta|poblacion|voto|eleccion",
                text,
            )
        )

    def _execute_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._selected_tool_names.append(name)
        self._tool_inputs.append({name: arguments})
        logger.info(
            "ask_soctrace_tool_call",
            extra={
                "selectedToolNames": [name],
                "toolInputs": [{name: arguments}],
            },
        )
        result = self.registry.execute(name, arguments)
        self._remember_entities(name, arguments, result)
        return result

    def _ensure_state(self, payload: AskRequest) -> ConversationState | None:
        if not payload.conversationId:
            return None
        state = conversation_store.get(payload.conversationId)
        if state is None:
            persistent_state = self._load_persistent_state(payload)
            if persistent_state is not None:
                conversation_store._states[payload.conversationId] = persistent_state
                state = persistent_state
        if state is None:
            state = conversation_store.get_or_create(payload.conversationId, payload.activeMunicipality or "29070")
        state.activeYear = payload.activeYear or state.activeYear
        if payload.selectedSectionId:
            section_name = payload.selectedSectionId
            state.lastSection = ConversationSection(sectionId=payload.selectedSectionId, sectionName=section_name)
            state.lastSections = [state.lastSection]
        state.touch()
        return state

    def _load_persistent_state(self, payload: AskRequest) -> ConversationState | None:
        if not payload.conversationId or not hasattr(self, "persistent_conversation_store"):
            return None
        if not getattr(self, "persistent_memory_available", True):
            return None
        try:
            conversation = self.persistent_conversation_store.get_or_create_conversation(
                session_id=payload.session_id or payload.conversationId,
                user_id=payload.user_id,
                municipio_id=payload.activeMunicipality or "29070",
                municipio_nombre="Mijas" if (payload.activeMunicipality or "29070") == "29070" else str(payload.activeMunicipality),
            )
            context = self.persistent_conversation_store.get_context(conversation.id)
            return conversation_memory_to_state(context)
        except Exception:
            self.persistent_memory_available = False
            logger.warning("ask_persistent_memory_load_failed", exc_info=False, extra={"session_id": payload.conversationId})
            return None

    def _followup_context_response(self, payload: AskRequest, state: ConversationState | None) -> AskResponse | None:
        resolution = self.follow_up_resolver.resolve(payload.question or "", state)
        if resolution is None:
            return None
        if resolution.intent in {"change_year", "ask_percentage"} and resolution.rerun_question:
            response = self._rerun_followup_question(payload, resolution.rerun_question)
            if resolution.answer_prefix and response.answer:
                response.answer = f"{resolution.answer_prefix} {response.answer[0].lower()}{response.answer[1:]}"
            return response
        if resolution.intent == "ask_table":
            if state and state.lastTable:
                return AskResponse(
                    answer=resolution.answer or "Claro. Te dejo la tabla del resultado anterior.",
                    mode=self._requested_response_mode(payload),
                    data={"fromPreviousContext": True},
                    methodology=state.lastMethodology,
                    caveats=state.lastCaveats,
                    sources=state.lastSources,
                    table=state.lastTable,
                    chartSpec=state.lastAnswerContext.chartSpec if state.lastAnswerContext else None,
                    debug=state.lastDebug if self._requested_response_mode(payload) == "debug" else None,
                )
            return AskResponse(
                answer="No tengo una tabla estructurada guardada para la respuesta anterior.",
                data={"fromPreviousContext": True},
            )
        if resolution.intent == "ask_methodology":
            methodology_answer = resolution.answer or "No tengo una metodología guardada para la respuesta anterior."
            if resolution.answer and not methodology_answer.lower().startswith("así lo he calculado"):
                methodology_answer = f"Así lo he calculado: {methodology_answer}"
            return AskResponse(
                answer=methodology_answer,
                mode=self._requested_response_mode(payload),
                data={"fromPreviousContext": True},
                methodology=state.lastMethodology if state else None,
                caveats=state.lastCaveats if state else [],
                sources=state.lastSources if state else [],
                table=state.lastTable if self._requested_response_mode(payload) == "detailed" and state else None,
                debug=state.lastDebug if self._requested_response_mode(payload) == "debug" and state else None,
            )
        if resolution.answer:
            return AskResponse(
                answer=resolution.answer,
                data={"fromPreviousContext": True},
                methodology=state.lastMethodology if state else None,
                caveats=state.lastCaveats if state else [],
                sources=state.lastSources if state else [],
            )
        return None

    def _rerun_followup_question(self, payload: AskRequest, rerun_question: str) -> AskResponse:
        self._skip_followup_once = True
        rerun_payload = AskRequest(
            question=rerun_question,
            conversationId=payload.conversationId,
            session_id=payload.session_id,
            user_id=payload.user_id,
            activeMunicipality=payload.activeMunicipality,
            activeYear=payload.activeYear,
            activeLayer=payload.activeLayer,
            selectedSectionId=payload.selectedSectionId,
            mode=payload.mode,
        )
        return self.ask(rerun_payload)

    def _previous_context_response(self, payload: AskRequest, state: ConversationState | None) -> AskResponse | None:
        if state is None or not state.lastAnswer:
            return None
        mode = self._requested_response_mode(payload)
        if mode == "simple":
            return None
        if not self._asks_for_previous_detail(payload.question or ""):
            return None
        answer = state.lastAnswer
        if self._asks_for_methodology(payload.question or "") and state.lastMethodology:
            answer = f"{state.lastAnswer}\n\nAsí lo he calculado: {state.lastMethodology}"
        elif self._asks_for_table(payload.question or "") and state.lastTable:
            answer = "Claro. Te dejo la tabla del resultado anterior."
        return AskResponse(
            answer=answer,
            mode=mode,
            data={"fromPreviousContext": True},
            methodology=state.lastMethodology,
            caveats=state.lastCaveats,
            sources=state.lastSources,
            table=state.lastTable,
            debug=state.lastDebug if mode == "debug" else None,
        )

    def _conversation_state(self, conversation_id: str | None) -> dict[str, Any]:
        state = conversation_store.get(conversation_id)
        return state.model_dump() if state else {}

    def _with_session_memory(self, payload: AskRequest, response: AskResponse) -> AskResponse:
        state = conversation_store.get(payload.conversationId)
        mode = self._requested_response_mode(payload)
        response.mode = mode
        response.shortCaveat = self._short_caveat(response.caveats)
        if mode == "debug":
            response.debug = response.debug or {
                "data": response.data,
                "sqlDebug": response.sqlDebug,
                "sources": response.sources,
                "confidence": response.confidence,
            }
        elif mode != "debug":
            response.debug = None
            if self.settings.app_env != "development":
                response.sqlDebug = None
        response.suggestedFollowUps = self._validated_suggested_questions(response.suggestedFollowUps, state)
        if response.suggestedFollowUps and not response.suggested_questions:
            response.suggested_questions = list(response.suggestedFollowUps)
        elif response.suggested_questions:
            response.suggested_questions = self._validated_suggested_questions(response.suggested_questions, state)
        if isinstance(response.data, dict) and isinstance(response.data.get("ctas"), list):
            response.data["ctas"] = self._validated_ctas(response.data["ctas"], state)
        if state:
            from_previous_context = isinstance(response.data, dict) and response.data.get("fromPreviousContext")
            if response.answer and not from_previous_context:
                state.lastAnswer = response.answer
                state.lastMethodology = response.methodology
                state.lastCaveats = list(response.caveats or [])
                state.lastSources = list(response.sources or [])
                state.lastTable = response.table
                state.lastDebug = {
                    "data": response.data,
                    "sqlDebug": response.sqlDebug,
                    "sources": response.sources,
                    "confidence": response.confidence,
                }
                state.lastAnswerContext = self._build_last_answer_context(payload, response, state)
                state.touch()
            response.session_memory = {
                "session_id": state.conversationId,
                "last_user_question": state.lastQuestion,
                "last_resolved_intent": state.lastResultType or state.analyticalContext.resultType,
                "last_dataset_scope": self._dataset_scope_from_metric(state.lastMetric),
                "last_geography_scope": "section" if state.lastSections or state.lastSection else "municipality",
                "last_time_scope": state.lastYear or state.activeYear,
                "last_metric": state.lastMetric,
                "last_dimension": "section",
                "last_result": state.lastResultRows[:1] if state.lastResultRows else state.lastResult,
                "last_sql": state.lastSql,
                "last_entities": {
                    "section": state.lastSection.model_dump() if state.lastSection else None,
                    "party": state.lastParty,
                    "age_range": state.lastAgeRange.model_dump() if state.lastAgeRange else None,
                },
                "conversation_summary": self._conversation_summary(state),
                "last_answer_context": state.lastAnswerContext.model_dump() if state.lastAnswerContext else None,
            }
        self._persist_response_memory(payload, response, state)
        return response

    def _persist_response_memory(self, payload: AskRequest, response: AskResponse, state: ConversationState | None) -> None:
        if not payload.conversationId or not hasattr(self, "persistent_conversation_store"):
            return
        if not getattr(self, "persistent_memory_available", True):
            response.session_id = payload.session_id or payload.conversationId
            return
        if isinstance(response.data, dict) and response.data.get("persistent_memory_saved"):
            response.conversation_id = response.data.get("conversation_id") or response.conversation_id
            response.session_id = response.data.get("session_id") or payload.session_id or payload.conversationId
            return
        try:
            conversation = self.persistent_conversation_store.get_or_create_conversation(
                session_id=payload.session_id or payload.conversationId,
                user_id=payload.user_id,
                municipio_id=payload.activeMunicipality or "29070",
                municipio_nombre="Mijas" if (payload.activeMunicipality or "29070") == "29070" else str(payload.activeMunicipality),
            )
            self.persistent_conversation_store.append_user_turn(conversation.id, payload.question or "")
            from_previous_context = isinstance(response.data, dict) and response.data.get("fromPreviousContext")
            if response.answer and not from_previous_context:
                tool_result = self._tool_result_from_response(response, state)
                self.persistent_conversation_store.append_assistant_turn(
                    conversation_id=conversation.id,
                    answer=response.answer,
                    tool_result=tool_result,
                    rendered_answer=None,
                    planner_metadata=self._planner_metadata_from_response(payload, response),
                )
            response.conversation_id = conversation.id
            response.session_id = conversation.session_id
            if isinstance(response.data, dict):
                response.data.setdefault("conversation_id", conversation.id)
                response.data.setdefault("session_id", conversation.session_id)
        except Exception:
            self.persistent_memory_available = False
            logger.warning("ask_persistent_memory_save_failed", exc_info=False, extra={"session_id": payload.conversationId})
            response.session_id = payload.session_id or payload.conversationId

    def _tool_result_from_response(self, response: AskResponse, state: ConversationState | None) -> ToolResult | None:
        data = response.data if isinstance(response.data, dict) else {}
        rows = data.get("rows") if isinstance(data.get("rows"), list) else self._rows_from_response(response)
        summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        if state:
            metadata = {
                **metadata,
                "metric": metadata.get("metric") or state.lastMetric,
                "party": metadata.get("party") or state.lastParty,
                "year": metadata.get("year") or state.lastYear,
                "start_year": metadata.get("start_year") or state.last_start_year,
                "end_year": metadata.get("end_year") or state.last_end_year,
                "sections": metadata.get("sections") or [section.model_dump() for section in state.lastSections],
            }
        tool_name = data.get("tool") or (state.last_tool_name if state else None) or (state.lastTool if state else None) or "unknown"
        operation = data.get("operation") or (state.last_operation if state else None) or (state.lastResultType if state else None) or "unknown"
        if not rows and not summary and tool_name == "unknown":
            return None
        return ToolResult(
            tool_name=str(tool_name),
            operation=str(operation),
            status="ok",
            rows=rows,
            summary=summary,
            metadata=metadata,
            chart_spec=response.chartSpec,
            methodology_plain=response.methodology,
            caveats=list(response.caveats or []),
            suggested_followups=list(response.suggestedFollowUps or []),
            sources=list(response.sources or []),
        )

    def _planner_metadata_from_response(self, payload: AskRequest, response: AskResponse) -> dict[str, Any]:
        data = response.data if isinstance(response.data, dict) else {}
        return {
            "provider": data.get("provider"),
            "model": data.get("model"),
            "complexity": json.dumps(data.get("complexity"), ensure_ascii=False) if isinstance(data.get("complexity"), dict) else data.get("complexity"),
            "tool_args": data.get("tool_args") if isinstance(data.get("tool_args"), dict) else {},
            "latency_ms": data.get("latency_ms"),
            "municipio_id": payload.activeMunicipality or "29070",
            "municipio_nombre": "Mijas" if (payload.activeMunicipality or "29070") == "29070" else str(payload.activeMunicipality),
        }

    def _build_last_answer_context(
        self,
        payload: AskRequest,
        response: AskResponse,
        state: ConversationState,
    ) -> LastAnswerContext:
        rows = state.lastResultRows or self._rows_from_response(response)
        first = rows[0] if rows else {}
        totals = response.data.get("totals") if isinstance(response.data, dict) and isinstance(response.data.get("totals"), dict) else {}
        response_data = response.data if isinstance(response.data, dict) else {}
        year = state.lastYear or self._int_or_none(first.get("year")) or payload.activeYear
        start_year = self._int_or_none(totals.get("startYear")) or self._int_or_none(first.get("start_year"))
        end_year = self._int_or_none(totals.get("endYear")) or self._int_or_none(first.get("end_year"))
        municipality_id = payload.activeMunicipality or state.municipality or str(first.get("municipio_id") or "29070")
        municipality_name = str(first.get("municipio_nombre") or ("Mijas" if municipality_id == "29070" else f"Municipio {municipality_id}"))
        metric = state.lastMetric or self._semantic_primary_metric(first) if first else state.lastMetric
        return LastAnswerContext(
            question=payload.question or "",
            answerSummary=self._summarize_answer(response.answer),
            operation=state.lastResultType or state.analyticalContext.resultType or "unknown",
            tool=response_data.get("tool") or state.last_tool_name or state.lastTool,
            metric=metric,
            metricLabel=self._metric_label(metric),
            municipality=MunicipalityContext(id=str(municipality_id), name=municipality_name),
            year=year if not (start_year and end_year) else None,
            startYear=start_year,
            endYear=end_year,
            election=ElectionContext(
                type=state.activeElection.type if state.activeElection else None,
                year=state.activeElection.year if state.activeElection else None,
            ) if state.activeElection else None,
            ageRange=state.lastAgeRange,
            sections=self._context_sections(rows, metric),
            resultRows=rows[:50],
            chartSpec=response.chartSpec,
            methodologyPlain=response.methodology,
            caveats=list(response.caveats or []),
            party=state.lastParty,
            provider=response_data.get("provider"),
            model=response_data.get("model"),
            createdAt=datetime.now(timezone.utc).isoformat(),
        )

    def _rows_from_response(self, response: AskResponse) -> list[dict[str, Any]]:
        if isinstance(response.data, dict) and isinstance(response.data.get("rows"), list):
            return [row for row in response.data["rows"] if isinstance(row, dict)]
        if isinstance(response.data, dict) and isinstance(response.data.get("results"), list):
            return [row for row in response.data["results"] if isinstance(row, dict)]
        if response.chartSpec and isinstance(response.chartSpec.get("rows"), list):
            return [row for row in response.chartSpec["rows"] if isinstance(row, dict)]
        return []

    def _context_sections(self, rows: list[dict[str, Any]], metric: str | None) -> list[ConversationSection]:
        sections: list[ConversationSection] = []
        for row in rows[:50]:
            section_id = row.get("section_id") or row.get("sectionId")
            section_name = row.get("section_name") or row.get("sectionName")
            if not section_id or not section_name:
                continue
            value = row.get(metric) if metric else None
            value_label = self._semantic_metric_value(metric, value) if metric and value is not None else None
            sections.append(
                ConversationSection(
                    sectionId=str(section_id),
                    sectionName=str(section_name),
                    value=value if isinstance(value, (int, float)) else None,
                    valueLabel=value_label,
                )
            )
        return sections

    def _metric_label(self, metric: str | None) -> str | None:
        if not metric:
            return None
        definition = self.sql_generator.semantic_catalog.metric(metric)
        if definition:
            return definition.label
        labels = {
            "growthAbs": "crecimiento absoluto",
            "growthPct": "crecimiento porcentual",
            "growth_abs": "crecimiento absoluto",
            "growth_pct": "crecimiento porcentual",
        }
        return labels.get(metric, metric)

    def _summarize_answer(self, answer: str) -> str:
        return re.split(r"\n\s*\n", answer.strip(), maxsplit=1)[0][:500] if answer else ""

    def _int_or_none(self, value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _validated_suggested_questions(self, questions: list[str], state: ConversationState | None = None) -> list[str]:
        valid: list[str] = []
        seen: set[str] = set()
        for question in questions:
            formatted = self._format_suggested_question(question)
            if formatted in seen:
                continue
            if self._suggestion_is_executable(formatted, state):
                valid.append(formatted)
                seen.add(formatted)
                continue
            fallback = self._suggestion_fallback(formatted, state)
            if fallback and fallback not in seen:
                valid.append(fallback)
                seen.add(fallback)
        return valid

    def _validated_ctas(self, ctas: list[dict[str, str]], state: ConversationState | None = None) -> list[dict[str, str]]:
        valid: list[dict[str, str]] = []
        seen: set[str] = set()
        for cta in ctas:
            question = self._format_suggested_question(str(cta.get("question") or cta.get("label") or ""))
            if not question or question in seen:
                continue
            if self._suggestion_is_executable(question, state):
                valid.append({**cta, "question": question})
                seen.add(question)
                continue
            fallback = self._suggestion_fallback(question, state)
            if fallback and fallback not in seen:
                valid.append({"label": str(cta.get("label") or "Ver alternativa"), "question": fallback})
                seen.add(fallback)
        return valid

    def _suggestion_is_executable(self, question: str, state: ConversationState | None = None) -> bool:
        if hasattr(self, "suggestion_validator"):
            result = self.suggestion_validator.validate(question, self._suggestion_context(state))
            if result.valid:
                return True
            logger.info(
                "ask_suggestion_validation_failed",
                extra={
                    "suggestion": question,
                    "validation_status": "failed",
                    "reason": result.reason or result.status,
                    "fallback_used": result.fallback_question,
                },
            )
            return False
        plan = self.sql_generator.generate(question, active_municipality="29070")
        return plan is not None

    def _suggestion_fallback(self, question: str, state: ConversationState | None = None) -> str | None:
        if not hasattr(self, "suggestion_validator"):
            return None
        result = self.suggestion_validator.validate(question, self._suggestion_context(state))
        fallback = result.fallback_question
        if not fallback:
            return None
        formatted = self._format_suggested_question(fallback)
        fallback_result = self.suggestion_validator.validate(formatted, self._suggestion_context(state))
        if fallback_result.valid:
            return formatted
        return None

    def _suggestion_context(self, state: ConversationState | None = None) -> dict[str, Any]:
        if not state:
            return {"activeMunicipality": "29070"}
        context = state.model_dump()
        context.setdefault("activeMunicipality", state.municipality or "29070")
        context.setdefault("lastParty", state.lastParty)
        context.setdefault("lastMetric", state.lastMetric)
        return context

    def _format_suggested_question(self, question: str) -> str:
        cleaned = question.strip().strip("•- ").rstrip(".")
        if not cleaned.startswith("¿"):
            cleaned = f"¿{cleaned}"
        if not cleaned.endswith("?"):
            cleaned = f"{cleaned}?"
        return cleaned

    def _requested_response_mode(self, payload: AskRequest) -> str:
        if payload.mode == "debug":
            return "debug" if self.settings.app_env == "development" and self.settings.ask_debug_enabled else "detailed"
        if payload.mode in {"simple", "detailed"}:
            return payload.mode
        question = payload.question or ""
        text = normalize(question)
        if self._asks_for_debug(text):
            return "debug" if self.settings.app_env == "development" and self.settings.ask_debug_enabled else "detailed"
        if self._asks_for_details(text) or self._asks_for_table(text) or self._asks_for_methodology(text):
            return "detailed"
        return "simple"

    def _asks_for_previous_detail(self, question: str) -> bool:
        text = normalize(question)
        return self._asks_for_methodology(text) or self._asks_for_table(text) or self._asks_for_details(text)

    def _asks_for_methodology(self, question: str) -> bool:
        text = normalize(question)
        return bool(re.search(r"como lo has calculado|c[oó]mo lo has calculado|metodolog|calculo|c[aá]lculo|fuentes", text))

    def _asks_for_table(self, question: str) -> bool:
        text = normalize(question)
        return bool(re.search(r"tabla|ranking|lista|ordena|ordename|ord[eé]name|desglosa|por seccion|por sección|detalle", text))

    def _asks_for_details(self, question: str) -> bool:
        text = normalize(question)
        return bool(re.search(r"explicame|expl[ií]came|dame el detalle|detalle|desglosa|ver fuentes|fuentes", text))

    def _asks_for_debug(self, question: str) -> bool:
        text = normalize(question)
        return bool(re.search(r"\bdebug\b|sql|execution plan|plan de ejecucion|plan de ejecución", text))

    def _short_caveat(self, caveats: list[str]) -> str | None:
        for caveat in caveats:
            text = normalize(caveat)
            if re.search(r"estimacion|estimaci[oó]n|ecologica|ecol[oó]gica|prorrate", text):
                if "ecol" in text:
                    return "Es una estimación territorial, no una medición individual de voto por edad."
                return "Es una estimación, porque el dataset trabaja con cohortes de edad agrupadas."
        return None

    def _dataset_scope_from_metric(self, metric: str | None) -> str | None:
        if metric in {"average_age", "population_under_30", "population_under_30_pct", "population_over_65", "population_over_65_pct"}:
            return "age_structure"
        if metric in {"abstention_pct", "participation_pct", "vote_pct", "winner_party"}:
            return "electoral_behavior"
        if metric in {"income_individual", "income_household"}:
            return "income"
        return None

    def _conversation_summary(self, state: ConversationState) -> str:
        bits = []
        if state.lastMetric:
            bits.append(f"metric={state.lastMetric}")
        if state.lastSection:
            bits.append(f"section={state.lastSection.sectionName}")
        if state.lastYear or state.activeYear:
            bits.append(f"year={state.lastYear or state.activeYear}")
        return "; ".join(bits)

    def _remember_entities(self, name: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
        conversation_store.update_from_tool(self._conversation_id, name, arguments, result)

    def _should_use_age_abstention_tool(self, payload: AskRequest) -> bool:
        text = normalize(payload.question)
        state = self._conversation_state(payload.conversationId)
        last_age_range = state.get("lastAgeRange") or {}
        active_election = state.get("activeElection") or {}
        has_age_range = bool(self._extract_age_range(payload.question)) or (
            last_age_range.get("minAge") is not None and re.search(r"esas personas|ese rango|esta cohorte|de esas", text)
        )
        has_abstention_or_vote = bool(
            re.search(r"abstencion|abstuv|abstener|no fueron a votar|no votar|no votaron|votantes|fueron a votar|votar|voto", text)
        )
        has_section_or_followup = bool(re.search(r"seccion|secciones|por secciones|ranking|orden", text)) or bool(
            re.search(r"esas personas|de esas|ese rango|esta cohorte", text)
        )
        has_election_context = bool(
            re.search(r"municipales|andaluzas|congreso|europeas|eleccion|electoral|2023", text)
        ) or active_election.get("type") is not None or bool(
            re.search(r"abstencion estimada|abstencion.*por seccion|ordena.*abstencion", text)
        )
        return has_age_range and has_abstention_or_vote and has_election_context

    def _resolve_age_abstention_params(self, payload: AskRequest) -> dict[str, Any]:
        state = self._conversation_state(payload.conversationId)
        last_age_range = state.get("lastAgeRange") or {}
        active_election = state.get("activeElection") or {}
        age_range = self._extract_age_range(payload.question)
        years = [int(match) for match in re.findall(r"\b(20\d{2})\b", payload.question)]
        return {
            "municipality": payload.activeMunicipality or state.get("municipality") or "Mijas",
            "year": years[0] if years else payload.activeYear or active_election.get("year") or state.get("activeYear") or 2023,
            "electionType": self._extract_election_type(payload.question) or active_election.get("type") or "municipales",
            "minAge": age_range[0] if age_range else last_age_range.get("minAge") or 18,
            "maxAge": age_range[1] if age_range else last_age_range.get("maxAge"),
            "groupBy": "section",
            "sortBy": "estimated_abstainers",
            "sortDirection": "asc" if re.search(r"menor a mayor|asc", normalize(payload.question)) else "desc",
        }

    def _extract_age_range(self, question: str) -> tuple[int, int | None] | None:
        text = normalize(question)
        if re.search(r"personas mayores|poblacion senior|jubilad", text):
            return (65, None)
        older_match = re.search(r"(?:mayores de|mas de|m[aá]s de)\s+(\d{1,3})", text)
        if older_match:
            age = int(older_match.group(1))
            return (age, None) if age < 120 else None
        plus_match = re.search(r"\b(\d{1,3})\s*(?:anos|años)?\s*o\s+m[aá]s\b", text)
        if plus_match:
            age = int(plus_match.group(1))
            return (age, None) if age < 120 else None
        under_match = re.search(r"(?:menores de|menos de)\s+(\d{1,3})", text)
        if under_match:
            age = int(under_match.group(1))
            return (0, max(age - 1, 0)) if age < 120 else None
        match = re.search(r"\b(\d{1,3})\s*(?:a|-)\s*(\d{1,3})\s*(?:anos|años)?\b", text)
        if not match:
            return None
        first = int(match.group(1))
        second = int(match.group(2))
        if first >= 120 or second >= 120:
            return None
        return (min(first, second), max(first, second))

    def _extract_election_type(self, question: str) -> str | None:
        text = normalize(question)
        if "andaluz" in text:
            return "andaluzas"
        if "congreso" in text or "generales" in text:
            return "congreso"
        if "europe" in text:
            return "europeas"
        if "municip" in text:
            return "municipales"
        return None


def _format_int(value: int | float | None) -> str:
    if value is None:
        return "no disponible"
    return f"{int(round(float(value))):,}".replace(",", ".")


def _format_decimal(value: int | float | None, decimals: int = 1) -> str:
    if value is None:
        return "no disponible"
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_signed_int(value: int | float | None) -> str:
    if value is None:
        return "no disponible"
    numeric = int(round(float(value)))
    sign = "+" if numeric > 0 else ""
    return f"{sign}{_format_int(numeric)}"


def _format_signed_decimal(value: int | float | None, decimals: int = 1) -> str:
    if value is None:
        return "no disponible"
    numeric = float(value)
    sign = "+" if numeric > 0 else ""
    return f"{sign}{_format_decimal(numeric, decimals)}"


def _average(values: list[Any]) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _first_number(rows: list[dict[str, Any]], key: str) -> float | None:
    for row in rows:
        if row.get(key) is not None:
            return float(row[key])
    return None


def get_ask_soctrace_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AskSocTraceService:
    return AskSocTraceService(session, settings)
