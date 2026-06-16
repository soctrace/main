from __future__ import annotations

import logging
import re
import time
import inspect
from typing import Any

from pydantic import ValidationError

from app.ask.answer_guard import AnswerGuard
from app.ask.conversation import PersistentConversationStore, conversation_memory_to_state, conversation_store
from app.ask.conversation.conversation_state import ConversationSection, LastAnswerContext, MunicipalityContext
from app.ask.conversation.follow_up_resolver import FollowUpResolver
from app.ask.llm.complexity_router import ComplexityRouter, ComplexityRouterInput
from app.ask.llm.prompts import PLANNER_PROMPT
from app.ask.llm.provider import LLMProvider
from app.ask.llm.schemas import LLMPlanRequest, LLMToolCall
from app.ask.planning import IntentGuard, ResultAnswerabilityGuard
from app.ask.rendering import AskRenderedAnswer, GeminiRenderer
from app.ask.tools_v2 import ToolContext, ToolExecutorV2, ToolResult, get_llm_tool_schemas
from app.ask.tools_v2.registry import ToolRegistryV2
from app.core.config import Settings
from app.schemas.ask import AskResponse


logger = logging.getLogger(__name__)


class AskPlannerLoop:
    def __init__(
        self,
        *,
        provider: LLMProvider,
        complexity_router: ComplexityRouter,
        tool_registry: ToolRegistryV2,
        tool_executor: ToolExecutorV2,
        follow_up_resolver: FollowUpResolver,
        answer_guard: AnswerGuard,
        settings: Settings,
        renderer: GeminiRenderer | None = None,
        persistent_store: PersistentConversationStore | None = None,
    ):
        self.provider = provider
        self.complexity_router = complexity_router
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.follow_up_resolver = follow_up_resolver
        self.answer_guard = answer_guard
        self.settings = settings
        self.renderer = renderer or GeminiRenderer(provider)
        self.persistent_store = persistent_store
        self.intent_guard = IntentGuard()
        self.result_guard = ResultAnswerabilityGuard()

    async def run(
        self,
        question: str,
        conversation_id: str | None,
        session_id: str | None = None,
        user_id: str | None = None,
        active_municipality: str = "29070",
        active_year: int | None = None,
        active_layer: str | None = None,
        locale: str = "es-ES",
    ) -> AskResponse | None:
        started = time.monotonic()
        persistent_conversation_id: str | None = None
        memory_session_id = session_id or conversation_id
        state_key = memory_session_id or conversation_id
        state = conversation_store.get_or_create(state_key, active_municipality) if state_key else None
        if self.persistent_store and memory_session_id:
            try:
                conversation = self.persistent_store.get_or_create_conversation(
                    session_id=memory_session_id,
                    user_id=user_id,
                    municipio_id=active_municipality,
                    municipio_nombre="Mijas" if active_municipality == "29070" else str(active_municipality),
                )
                persistent_conversation_id = conversation.id
                persistent_context = self.persistent_store.get_context(conversation.id)
                state = conversation_memory_to_state(persistent_context)
                conversation_store._states[memory_session_id] = state
                self.persistent_store.append_user_turn(conversation.id, question)
            except Exception:
                logger.exception("ask_llm_persistent_memory_load_failed", extra={"session_id": memory_session_id})
        followup = self.follow_up_resolver.resolve(question, state)
        if followup and followup.answer:
            return AskResponse(answer=followup.answer, data={"fromPreviousContext": True})

        complexity_result = self.complexity_router.classify(
            ComplexityRouterInput(
                question=question,
                locale=locale,
                conversation_context=self._conversation_context_summary(state),
                active_municipality=active_municipality,
                active_year=active_year,
            )
        )
        tools = get_llm_tool_schemas(include_beta=True)
        conversation_context = self._conversation_context_summary(state)
        semantic_context = self._semantic_context(active_municipality, active_year, active_layer, conversation_context)
        max_attempts = max(1, int(self.settings.ask_llm_max_planning_attempts or 1))
        last_error_hint: str | None = None
        last_tool_result: ToolResult | None = None
        observability: dict[str, Any] = {
            "question": question,
            "planner": self.provider.name,
            "tool_selected": None,
            "tool_args": {},
            "intent_guard": "not_run",
            "result_guard": "not_run",
            "fallback_used": False,
            "final_status": "started",
        }

        for attempt in range(1, max_attempts + 1):
            plan_request = LLMPlanRequest(
                question=question,
                system_prompt=self._planner_prompt(last_error_hint),
                conversation_context=conversation_context,
                semantic_context=semantic_context,
                tools=tools,
                complexity=complexity_result.complexity,
                locale=locale,
            )
            plan_response = await self.provider.plan(plan_request)
            if plan_response.tool_call is None:
                if self._requires_tool(question):
                    last_error_hint = "La pregunta requiere una herramienta. Devuelve exactamente una function call válida."
                    continue
                if self._deterministic_plan(question, active_municipality, active_year):
                    break
                return None

            tool_call = plan_response.tool_call
            observability["tool_selected"] = tool_call.tool_name
            observability["tool_args"] = tool_call.arguments

            intent_guard = self.intent_guard.validate_tool_choice(question, tool_call.tool_name, tool_call.arguments, semantic_context)
            observability["intent_guard"] = "passed" if intent_guard.ok else "failed"
            if not intent_guard.ok:
                logger.warning(
                    "ask_llm_intent_guard_failed",
                    extra={**observability, "reasons": intent_guard.reasons, "repair_hint": intent_guard.repair_hint},
                )
                last_error_hint = intent_guard.repair_hint or "; ".join(intent_guard.reasons)
                continue

            validation_error = self._validate_tool_call(tool_call.tool_name, tool_call.arguments)
            if validation_error:
                last_error_hint = validation_error
                continue

            context = ToolContext(
                municipio_id=active_municipality,
                municipio_nombre="Mijas" if active_municipality == "29070" else None,
                locale=locale,
                active_year=active_year,
                conversation_id=memory_session_id,
            )
            maybe_tool_result = self.tool_executor.execute(tool_call.tool_name, tool_call.arguments, context)
            tool_result = await maybe_tool_result if inspect.isawaitable(maybe_tool_result) else maybe_tool_result
            last_tool_result = tool_result
            result_guard = self.result_guard.validate(question, tool_call.tool_name, tool_call.arguments, tool_result)
            observability["result_guard"] = "passed" if result_guard.ok else "failed"
            if not result_guard.ok:
                logger.warning(
                    "ask_llm_result_guard_failed",
                    extra={**observability, "reasons": result_guard.reasons, "repair_hint": result_guard.repair_hint},
                )
                last_error_hint = result_guard.repair_hint or "; ".join(result_guard.reasons)
                continue
            if tool_result.status == "empty":
                return self._empty_response(tool_result)
            if tool_result.status == "unsupported":
                observability["final_status"] = "unsupported"
                logger.info("ask_llm_observability", extra=observability)
                return self._unsupported_response(tool_result)
            if tool_result.status == "error":
                logger.error("ask_llm_tool_execution_error", extra={"tool": tool_result.tool_name, "error_code": tool_result.error_code})
                return None

            tool_guard = self.answer_guard.validate_tool_result(
                question,
                tool_call.tool_name,
                tool_call.arguments,
                tool_result,
            )
            if not tool_guard.ok:
                logger.warning("ask_llm_tool_guard_failed", extra={"reasons": tool_guard.reasons, "tool": tool_result.tool_name})
            rendered = await self.renderer.render(
                question=question,
                tool_result=tool_result,
                conversation_context=conversation_context,
                response_style="detailed",
                locale=locale,
            )
            if not tool_guard.ok:
                rendered.metadata["tool_guard_reasons"] = tool_guard.reasons
            response = self._response_from_rendered(
                rendered=rendered,
                question=question,
                tool_result=tool_result,
                provider_model=plan_response.model,
                complexity=complexity_result.model_dump(),
                tool_args=tool_call.arguments,
                latency_ms=int((time.monotonic() - started) * 1000),
                guard_reasons=tool_guard.reasons,
            )

            self._remember_result(state, question, tool_result, response, plan_response.model, tool_call.arguments)
            self._persist_planner_turn(
                persistent_conversation_id,
                response,
                tool_result,
                rendered,
                {
                    "provider": self.provider.name,
                    "model": plan_response.model,
                    "complexity": complexity_result.complexity,
                    "tool_args": tool_call.arguments,
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "guard_reasons": tool_guard.reasons,
                    "renderer_guard_reasons": response.data.get("renderer_guard_reasons", []) if isinstance(response.data, dict) else [],
                    "renderer_fallback_reason": response.data.get("renderer_fallback_reason") if isinstance(response.data, dict) else None,
                },
            )
            logger.info(
                "ask_llm_planner_loop",
                extra={
                    "conversation_id": conversation_id,
                    "question": question,
                    "complexity": complexity_result.complexity,
                    "provider": self.provider.name,
                    "model": plan_response.model,
                    "planning_attempts": attempt,
                    "tool_name": tool_result.tool_name,
                    "tool_args": tool_call.arguments,
                    "tool_status": tool_result.status,
                    "rows": len(tool_result.rows),
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "fallback_used": False,
                    "guard_passed": tool_guard.ok and not response.data.get("renderer_guard_reasons"),
                },
            )
            observability["final_status"] = "ok"
            logger.info("ask_llm_observability", extra=observability)
            return response

        fallback_call = self._deterministic_plan(question, active_municipality, active_year)
        if fallback_call:
            fallback_response = await self._run_tool_call(
                question=question,
                tool_call=fallback_call,
                conversation_context=conversation_context,
                complexity=complexity_result.model_dump(),
                state=state,
                persistent_conversation_id=persistent_conversation_id,
                started=started,
                memory_session_id=memory_session_id,
                active_municipality=active_municipality,
                active_year=active_year,
                locale=locale,
                observability={**observability, "fallback_used": True, "planner": "deterministic"},
            )
            if fallback_response:
                return fallback_response

        if last_tool_result and last_tool_result.status == "empty":
            observability["final_status"] = "empty"
            logger.info("ask_llm_observability", extra=observability)
            return self._empty_response(last_tool_result)
        observability["final_status"] = "unsupported"
        logger.info("ask_llm_observability", extra=observability)
        return None

    async def _run_tool_call(
        self,
        *,
        question: str,
        tool_call: LLMToolCall,
        conversation_context: dict[str, Any],
        complexity: dict[str, Any],
        state: Any | None,
        persistent_conversation_id: str | None,
        started: float,
        memory_session_id: str | None,
        active_municipality: str,
        active_year: int | None,
        locale: str,
        observability: dict[str, Any],
    ) -> AskResponse | None:
        observability["tool_selected"] = tool_call.tool_name
        observability["tool_args"] = tool_call.arguments
        validation_error = self._validate_tool_call(tool_call.tool_name, tool_call.arguments)
        if validation_error:
            logger.warning("ask_llm_fallback_validation_failed", extra={**observability, "error": validation_error})
            return None
        intent_guard = self.intent_guard.validate_tool_choice(question, tool_call.tool_name, tool_call.arguments)
        observability["intent_guard"] = "passed" if intent_guard.ok else "failed"
        if not intent_guard.ok:
            logger.warning("ask_llm_fallback_intent_guard_failed", extra={**observability, "reasons": intent_guard.reasons})
            return None

        context = ToolContext(
            municipio_id=active_municipality,
            municipio_nombre="Mijas" if active_municipality == "29070" else None,
            locale=locale,
            active_year=active_year,
            conversation_id=memory_session_id,
        )
        maybe_tool_result = self.tool_executor.execute(tool_call.tool_name, tool_call.arguments, context)
        tool_result = await maybe_tool_result if inspect.isawaitable(maybe_tool_result) else maybe_tool_result
        result_guard = self.result_guard.validate(question, tool_call.tool_name, tool_call.arguments, tool_result)
        observability["result_guard"] = "passed" if result_guard.ok else "failed"
        if not result_guard.ok:
            logger.warning(
                "ask_llm_fallback_result_guard_failed",
                extra={**observability, "status": tool_result.status, "reasons": result_guard.reasons},
            )
            if tool_result.status == "empty":
                observability["final_status"] = "empty"
                logger.info("ask_llm_observability", extra=observability)
                return self._empty_response(tool_result)
            return None
        if tool_result.status == "unsupported":
            observability["final_status"] = "unsupported"
            logger.info("ask_llm_observability", extra=observability)
            return self._unsupported_response(tool_result)
        if tool_result.status == "error":
            observability["final_status"] = "error"
            logger.info("ask_llm_observability", extra=observability)
            return None

        tool_guard = self.answer_guard.validate_tool_result(question, tool_call.tool_name, tool_call.arguments, tool_result)
        rendered = await self.renderer.render(
            question=question,
            tool_result=tool_result,
            conversation_context=conversation_context,
            response_style="detailed",
            locale=locale,
        )
        if not tool_guard.ok:
            rendered.metadata["tool_guard_reasons"] = tool_guard.reasons
        response = self._response_from_rendered(
            rendered=rendered,
            question=question,
            tool_result=tool_result,
            provider_model="deterministic-fallback",
            complexity=complexity,
            tool_args=tool_call.arguments,
            latency_ms=int((time.monotonic() - started) * 1000),
            guard_reasons=tool_guard.reasons,
        )
        self._remember_result(state, question, tool_result, response, "deterministic-fallback", tool_call.arguments)
        self._persist_planner_turn(
            persistent_conversation_id,
            response,
            tool_result,
            rendered,
            {
                "provider": "deterministic",
                "model": "deterministic-fallback",
                "tool_args": tool_call.arguments,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "fallback_used": True,
                "guard_reasons": tool_guard.reasons,
            },
        )
        observability["final_status"] = "ok"
        logger.info("ask_llm_observability", extra=observability)
        return response

    def _persist_planner_turn(
        self,
        conversation_id: str | None,
        response: AskResponse,
        tool_result: ToolResult,
        rendered: AskRenderedAnswer,
        planner_metadata: dict[str, Any],
    ) -> None:
        if not conversation_id or not self.persistent_store:
            return
        try:
            self.persistent_store.append_assistant_turn(
                conversation_id=conversation_id,
                answer=response.answer,
                tool_result=tool_result,
                rendered_answer=rendered,
                planner_metadata=planner_metadata,
            )
            response.conversation_id = conversation_id
            response.session_id = self.persistent_store.get_conversation(conversation_id).session_id
            if isinstance(response.data, dict):
                response.data["persistent_memory_saved"] = True
                response.data["conversation_id"] = conversation_id
                response.data["session_id"] = response.session_id
        except Exception:
            logger.exception("ask_llm_persistent_memory_save_failed", extra={"conversation_id": conversation_id})

    def _validate_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> str | None:
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return f"La herramienta `{tool_name}` no existe. Usa solo herramientas disponibles."
        if getattr(tool, "status", "supported") not in {"supported", "beta"}:
            return f"La herramienta `{tool_name}` no está activa."
        try:
            tool.input_schema.model_validate(arguments)
        except ValidationError as exc:
            return f"Argumentos inválidos para `{tool_name}`: {exc.errors()[:3]}"
        return None

    def _deterministic_plan(self, question: str, active_municipality: str, active_year: int | None = None) -> LLMToolCall | None:
        text = self._normalized_question(question)
        base = {"municipio_id": active_municipality}

        if re.search(r"seccion mas poblada|mas poblada|mayor poblacion|mas habitantes", text):
            return LLMToolCall(
                tool_name="rank_sections",
                arguments={**base, "metric": "population_total", "order": "desc", "year": active_year or 2025, "limit": 1},
            )
        if re.search(r"menor abstencion", text):
            return LLMToolCall(tool_name="rank_sections", arguments={**base, "metric": "abstention_pct", "order": "asc", "election_type": "MUNICIPALES", "limit": 5})
        if re.search(r"mayor abstencion", text):
            return LLMToolCall(tool_name="rank_sections", arguments={**base, "metric": "abstention_pct", "order": "desc", "election_type": "MUNICIPALES", "limit": 5})
        if re.search(r"mayor participacion|donde vota mas", text):
            return LLMToolCall(tool_name="rank_sections", arguments={**base, "metric": "participation_pct", "order": "desc", "election_type": "MUNICIPALES", "limit": 5})
        if re.search(r"menor participacion|donde vota menos", text):
            return LLMToolCall(tool_name="rank_sections", arguments={**base, "metric": "participation_pct", "order": "asc", "election_type": "MUNICIPALES", "limit": 5})
        if re.search(r"18 anos en 2027|personas tendran 18", text):
            return LLMToolCall(
                tool_name="age_cohort_projection",
                arguments={
                    **base,
                    "source_year": 2025,
                    "source_age": 16,
                    "target_year": 2027,
                    "target_age": 18,
                    "group_by": "municipality_and_section",
                    "limit": 5,
                },
            )
        if re.search(r"18\s*(a|-|y)\s*22|entre 18 y 22", text):
            year_match = re.search(r"\b(20\d{2})\b", text)
            return LLMToolCall(
                tool_name="age_cohort_projection",
                arguments={
                    **base,
                    "min_age": 18,
                    "max_age": 22,
                    "source_year": int(year_match.group(1)) if year_match else 2023,
                    "group_by": "municipality_and_section",
                    "limit": 5,
                },
            )
        if re.search(r"que suelen votar|que votan|voto de los jovenes|voto de los mayores|mayores de 45|menores de 30", text):
            min_age = 45 if "mayores de 45" in text or "voto de los mayores" in text else None
            max_age = 29 if "menores de 30" in text or "voto de los jovenes" in text else None
            return LLMToolCall(
                tool_name="ecological_vote_profile_by_age_group",
                arguments={**base, "min_age": min_age, "max_age": max_age, "election_type": "MUNICIPALES", "party_scope": "main"},
            )
        return None

    def _normalized_question(self, question: str) -> str:
        import unicodedata

        text = question.lower()
        return "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")

    def _requires_tool(self, question: str) -> bool:
        if not self.settings.ask_llm_require_tool_for_numeric:
            return False
        return bool(
            re.search(
                r"cu[aá]nt|cu[aá]l|qu[eé] secciones|ranking|media|porcentaje|evoluci[oó]n|crecido|correlaci[oó]n|proyecci[oó]n|voto|abstenci[oó]n|renta|poblaci[oó]n",
                question.lower(),
            )
        )

    def _planner_prompt(self, error_hint: str | None) -> str:
        if not error_hint:
            return PLANNER_PROMPT
        return f"{PLANNER_PROMPT}\n\nCorrección necesaria del intento anterior: {error_hint}"

    def _conversation_context_summary(self, state: Any | None) -> dict[str, Any]:
        if state is None:
            return {}
        return {
            "last_question": state.lastQuestion,
            "last_tool": state.last_tool_name or state.lastTool,
            "last_operation": state.last_operation,
            "last_metric": state.lastMetric,
            "last_year": state.lastYear,
            "last_party": state.lastParty,
            "last_sections": [section.model_dump() for section in state.lastSections[:10]],
            "last_answer_context": state.lastAnswerContext.model_dump() if state.lastAnswerContext else None,
        }

    def _semantic_context(self, active_municipality: str, active_year: int | None, active_layer: str | None, recent_context: dict[str, Any]) -> dict[str, Any]:
        return {
            "active_municipality": "Mijas" if active_municipality == "29070" else active_municipality,
            "active_municipality_id": active_municipality,
            "active_year": active_year,
            "active_layer": active_layer,
            "available_domains": ["population", "age", "income", "electoral", "housing"],
            "known_metrics": [
                "population_total",
                "average_age",
                "population_over_65",
                "population_under_30",
                "income_individual",
                "abstention_pct",
                "participation_pct",
                "market_price_estimated_m2",
            ],
            "recent_context": recent_context,
        }

    def _response_from_tool_result(
        self,
        *,
        question: str,
        tool_result: ToolResult,
        provider_model: str,
        complexity: dict[str, Any],
        tool_args: dict[str, Any],
        latency_ms: int,
        guard_reasons: list[str] | None = None,
    ) -> AskResponse:
        rows = tool_result.rows or []
        answer = self._deterministic_answer(tool_result)
        table_rows = rows[:15]
        table = {
            "title": tool_result.summary.get("value_label") or tool_result.operation,
            "columns": list(table_rows[0].keys()) if table_rows else [],
            "rows": [[row.get(column) for column in table_rows[0].keys()] for row in table_rows] if table_rows else [],
        } if table_rows else None
        entities = [
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
        return AskResponse(
            answer=answer,
            confidence="medium" if tool_result.tool_name in {"cross_metric_ranking", "correlation_analysis"} else "high",
            resultType="entity_list" if entities else "single_value",
            entities=entities,
            data={
                "tool": tool_result.tool_name,
                "operation": tool_result.operation,
                "rows": rows,
                "summary": tool_result.summary,
                "metadata": tool_result.metadata,
                "provider": self.provider.name,
                "model": provider_model,
                "complexity": complexity,
                "tool_args": tool_args,
                "latency_ms": latency_ms,
                "guard_reasons": guard_reasons or [],
                "explanation": tool_result.explanation.model_dump() if tool_result.explanation else None,
                "metric_explanations": [item.model_dump() for item in tool_result.metric_explanations],
                "score_explanation": tool_result.score_explanation.model_dump() if tool_result.score_explanation else None,
            },
            methodology=tool_result.methodology_plain,
            caveats=tool_result.caveats,
            sources=tool_result.sources,
            suggestedFollowUps=tool_result.suggested_followups,
            table=table,
            chartSpec=tool_result.chart_spec,
        )

    def _response_from_rendered(
        self,
        *,
        rendered: AskRenderedAnswer,
        question: str,
        tool_result: ToolResult,
        provider_model: str,
        complexity: dict[str, Any],
        tool_args: dict[str, Any],
        latency_ms: int,
        guard_reasons: list[str] | None = None,
    ) -> AskResponse:
        result_type = "entity_list" if rendered.entities else "single_value"
        metadata = {
            **(tool_result.metadata or {}),
            **(rendered.metadata or {}),
        }
        return AskResponse(
            answer=rendered.answer,
            mode=rendered.mode,
            confidence="medium" if tool_result.tool_name in {"cross_metric_ranking", "correlation_analysis"} else "high",
            resultType=result_type,
            entities=rendered.entities,
            data={
                "tool": tool_result.tool_name,
                "operation": tool_result.operation,
                "rows": tool_result.rows,
                "summary": tool_result.summary,
                "metadata": metadata,
                "provider": self.provider.name,
                "model": provider_model,
                "complexity": complexity,
                "tool_args": tool_args,
                "latency_ms": latency_ms,
                "guard_reasons": guard_reasons or [],
                "renderer_guard_reasons": metadata.get("renderer_guard_reasons", []),
                "renderer_fallback_reason": metadata.get("renderer_fallback_reason"),
            },
            shortCaveat=rendered.short_caveat,
            methodology=rendered.methodology,
            caveats=rendered.caveats,
            sources=tool_result.sources,
            suggestedFollowUps=rendered.suggested_followups,
            suggested_questions=rendered.suggested_followups,
            table=rendered.table,
            chartSpec=rendered.chart_spec,
        )

    def _empty_response(self, tool_result: ToolResult) -> AskResponse:
        metric = (tool_result.metadata or {}).get("metric")
        if metric in {"abstention_pct", "participation_pct"}:
            answer = (
                "He buscado el ranking electoral usando la última elección municipal disponible, pero no he encontrado filas válidas. "
                "Esto puede indicar que la vista electoral no tiene esa métrica calculada para ese proceso. "
                "Puedo probar con todas las elecciones disponibles o revisar la capa electoral."
            )
        else:
            answer = (
                "He entendido la consulta, pero no hay datos para ese filtro concreto. "
                "No he encontrado datos para ese filtro concreto. "
                "Puedo probar con la última elección municipal disponible o con todas las elecciones disponibles."
            )
        return AskResponse(
            answer=answer,
            confidence="medium",
            data={"tool": tool_result.tool_name, "operation": tool_result.operation, "rows": []},
            methodology=tool_result.methodology_plain,
            caveats=tool_result.caveats,
            sources=tool_result.sources,
        )

    def _unsupported_response(self, tool_result: ToolResult) -> AskResponse:
        safe_reason = ""
        if tool_result.error_code not in {"unknown_tool", "pending_tool", "invalid_tool_arguments"} and tool_result.caveats:
            safe_reason = f" {tool_result.caveats[0]}"
        return AskResponse(
            answer="He entendido la consulta, pero ahora mismo no puedo calcularla con las herramientas activas." + safe_reason,
            confidence="low",
            data={
                "tool": tool_result.tool_name,
                "operation": tool_result.operation,
                "status": tool_result.status,
                "error_code": tool_result.error_code,
            },
            methodology=tool_result.methodology_plain,
            caveats=tool_result.caveats,
            sources=tool_result.sources,
        )

    def _deterministic_answer(self, tool_result: ToolResult) -> str:
        rows = tool_result.rows or []
        if not rows:
            return "No hay resultados para la operación solicitada."
        first = rows[0]
        if tool_result.summary.get("answer"):
            return str(tool_result.summary["answer"])
        if tool_result.tool_name == "cross_metric_ranking":
            variables = tool_result.metric_explanations[:2]
            variable_label = " y ".join(item.label.lower() for item in variables) if variables else "los factores solicitados"
            bullets = "\n".join(f"• {row.get('section_name')} — {row.get('value')}" for row in rows[:5])
            score = tool_result.score_explanation
            return (
                f"La sección que mejor combina {variable_label} es {first.get('section_name')}.\n\n"
                f"Resultados principales\n\n{bullets}\n\n"
                "Qué significa\n\nEl resultado combina los factores solicitados para ordenar las secciones donde coinciden con más intensidad.\n\n"
                f"Cómo se ha calculado\n\nEl índice combinado va de {score.scale if score else '0 a 1'}: cuanto más cerca está de 1, más intensa es la combinación de factores. "
                "No es un porcentaje ni una probabilidad.\n\n"
                "Interpretación útil\n\nEstas zonas sirven para priorizar análisis territorial o movilización.\n\n"
                "Cautela metodológica\n\n• No demuestra causalidad.\n• No mide voto individual; es una lectura territorial por sección."
            )
        label = first.get("value_label") or tool_result.summary.get("value_label") or "valor"
        value = first.get("value")
        section = first.get("section_name") or first.get("name")
        if section and value is not None:
            return f"El resultado principal es {section}, con {label}: {value}."
        if section:
            return f"El resultado principal es {section}."
        if value is not None:
            return f"El resultado municipal es {value} ({label})."
        return "He obtenido resultados estructurados de la herramienta seleccionada."

    def _remember_result(
        self,
        state: Any | None,
        question: str,
        tool_result: ToolResult,
        response: AskResponse,
        model: str,
        tool_args: dict[str, Any],
    ) -> None:
        if state is None:
            return
        rows = tool_result.rows or []
        first = rows[0] if rows else {}
        state.lastQuestion = question
        state.lastTool = tool_result.tool_name
        state.last_tool_name = tool_result.tool_name
        state.last_operation = tool_result.operation
        state.lastResultType = tool_result.operation
        state.lastMetric = tool_args.get("metric") or tool_args.get("x_metric") or tool_result.metadata.get("metric")
        state.lastYear = first.get("year") or tool_result.metadata.get("year")
        state.last_start_year = first.get("start_year") or tool_result.metadata.get("start_year")
        state.last_end_year = first.get("end_year") or tool_result.metadata.get("end_year")
        state.lastParty = tool_args.get("party") or tool_result.metadata.get("party")
        state.last_party = state.lastParty
        state.lastResultRows = rows
        state.last_rows = rows
        state.lastResult = {"tool": tool_result.tool_name, "rows": rows, "summary": tool_result.summary}
        state.last_chart_spec = tool_result.chart_spec
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
        state.lastAnswer = response.answer
        state.lastMethodology = response.methodology
        state.lastCaveats = list(response.caveats or [])
        state.lastSources = list(response.sources or [])
        state.lastTable = response.table
        state.lastDebug = {"provider": self.provider.name, "model": model, "tool_args": tool_args}
        state.lastAnswerContext = LastAnswerContext(
            question=question,
            answerSummary=response.answer[:240],
            operation=tool_result.operation,
            tool=tool_result.tool_name,
            metric=state.lastMetric,
            municipality=MunicipalityContext(id=state.municipality or "29070", name="Mijas" if (state.municipality or "29070") == "29070" else str(state.municipality)),
            year=state.lastYear,
            startYear=state.last_start_year,
            endYear=state.last_end_year,
            sections=state.lastSections,
            resultRows=rows[:50],
            chartSpec=response.chartSpec,
            methodologyPlain=response.methodology,
            caveats=list(response.caveats or []),
            party=state.lastParty,
            provider=self.provider.name,
            model=model,
        )
        state.touch()
