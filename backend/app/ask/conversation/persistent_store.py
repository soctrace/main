from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ask.conversation.schemas import ConversationMemoryContext, ConversationRecord, TurnRecord
from app.ask.rendering.answer_contract import AskRenderedAnswer
from app.ask.tools_v2.schemas import ToolResult


logger = logging.getLogger(__name__)

MAX_STORED_RESULT_ROWS = 50


class PersistentMemoryUnavailable(RuntimeError):
    pass


class PersistentConversationStore:
    def __init__(self, session: Session):
        self.session = session
        self._dialect = session.bind.dialect.name if session.bind is not None else "postgresql"

    def get_or_create_conversation(
        self,
        session_id: str,
        user_id: str | None = None,
        municipio_id: str = "29070",
        municipio_nombre: str = "Mijas",
    ) -> ConversationRecord:
        if user_id is None:
            existing = self._fetch_one(
                """
                SELECT * FROM core.agent_conversations
                WHERE session_id = :session_id
                  AND user_id IS NULL
                  AND status = 'active'
                ORDER BY last_active_at DESC
                LIMIT 1
                """,
                {"session_id": session_id},
            )
        else:
            existing = self._fetch_one(
                """
                SELECT * FROM core.agent_conversations
                WHERE session_id = :session_id
                  AND user_id = :user_id
                  AND status = 'active'
                ORDER BY last_active_at DESC
                LIMIT 1
                """,
                {"session_id": session_id, "user_id": user_id},
            )
        if existing:
            self._execute(
                """
                UPDATE core.agent_conversations
                SET municipio_id = :municipio_id,
                    municipio_nombre = :municipio_nombre,
                    updated_at = CURRENT_TIMESTAMP,
                    last_active_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """,
                {
                    "id": existing["id"],
                    "municipio_id": municipio_id,
                    "municipio_nombre": municipio_nombre,
                },
            )
            self.session.commit()
            existing["municipio_id"] = municipio_id
            existing["municipio_nombre"] = municipio_nombre
            return ConversationRecord.model_validate(self._decode_record(existing))

        conversation_id = str(uuid.uuid4())
        self._execute(
            """
            INSERT INTO core.agent_conversations (
                id, user_id, session_id, municipio_id, municipio_nombre, metadata
            ) VALUES (
                :id, :user_id, :session_id, :municipio_id, :municipio_nombre, :metadata
            )
            """,
            {
                "id": conversation_id,
                "user_id": user_id,
                "session_id": session_id,
                "municipio_id": municipio_id,
                "municipio_nombre": municipio_nombre,
                "metadata": self._json_param({}),
            },
        )
        self.session.commit()
        return self.get_conversation(conversation_id)

    def get_conversation(self, conversation_id: str) -> ConversationRecord:
        row = self._fetch_one("SELECT * FROM core.agent_conversations WHERE id = :id", {"id": conversation_id})
        if not row:
            raise ValueError(f"Conversation {conversation_id} not found")
        return ConversationRecord.model_validate(self._decode_record(row))

    def append_user_turn(self, conversation_id: str, question: str) -> TurnRecord:
        return self._append_turn(conversation_id=conversation_id, role="user", question=question)

    def append_assistant_turn(
        self,
        conversation_id: str,
        answer: str,
        tool_result: ToolResult | None = None,
        rendered_answer: AskRenderedAnswer | None = None,
        planner_metadata: dict[str, Any] | None = None,
    ) -> TurnRecord:
        planner_metadata = self._safe_metadata(planner_metadata or {})
        metadata = dict(tool_result.metadata or {}) if tool_result else {}
        rows = list(tool_result.rows or []) if tool_result else []
        stored_rows = rows[:MAX_STORED_RESULT_ROWS]
        summary = dict(tool_result.summary or {}) if tool_result else {}
        if len(rows) > len(stored_rows):
            summary["rows_truncated"] = True
            summary["rows_total"] = len(rows)
        sections = metadata.get("sections") or self._sections_from_rows(stored_rows)
        return self._append_turn(
            conversation_id=conversation_id,
            role="assistant",
            answer=answer,
            operation=(tool_result.operation if tool_result else None) or planner_metadata.get("operation"),
            tool_name=(tool_result.tool_name if tool_result else None) or planner_metadata.get("tool_name"),
            provider=planner_metadata.get("provider"),
            model=planner_metadata.get("model"),
            complexity=planner_metadata.get("complexity"),
            metric=metadata.get("metric") or planner_metadata.get("metric"),
            metric_label=metadata.get("metric_label") or metadata.get("value_label") or planner_metadata.get("metric_label"),
            municipio_id=metadata.get("municipio_id") or planner_metadata.get("municipio_id"),
            municipio_nombre=metadata.get("municipio_nombre") or planner_metadata.get("municipio_nombre"),
            year=self._int_or_none(metadata.get("year") or planner_metadata.get("year")),
            start_year=self._int_or_none(metadata.get("start_year") or planner_metadata.get("start_year")),
            end_year=self._int_or_none(metadata.get("end_year") or planner_metadata.get("end_year")),
            party=metadata.get("party") or planner_metadata.get("party"),
            election_type=metadata.get("election_type") or planner_metadata.get("election_type"),
            election_year=self._int_or_none(metadata.get("election_year") or planner_metadata.get("election_year")),
            sections=sections,
            result_rows=stored_rows,
            summary=summary,
            chart_spec=(rendered_answer.chart_spec if rendered_answer else None) or (tool_result.chart_spec if tool_result else None),
            methodology_plain=(rendered_answer.methodology if rendered_answer else None) or (tool_result.methodology_plain if tool_result else None),
            caveats=(rendered_answer.caveats if rendered_answer else None) or (tool_result.caveats if tool_result else []),
            suggested_followups=(rendered_answer.suggested_followups if rendered_answer else None) or (tool_result.suggested_followups if tool_result else []),
            tool_args=planner_metadata.get("tool_args") or {},
            tool_result_status=tool_result.status if tool_result else None,
            guard_result={
                "tool_guard_reasons": planner_metadata.get("guard_reasons") or [],
                "renderer_guard_reasons": planner_metadata.get("renderer_guard_reasons") or [],
                "renderer_fallback_reason": planner_metadata.get("renderer_fallback_reason"),
            },
            latency_ms=self._int_or_none(planner_metadata.get("latency_ms")),
        )

    def get_context(self, conversation_id: str, limit: int = 8) -> ConversationMemoryContext:
        conversation = self.get_conversation(conversation_id)
        turns = self._fetch_all(
            """
            SELECT * FROM core.agent_turns
            WHERE conversation_id = :conversation_id
            ORDER BY turn_index DESC
            LIMIT :limit
            """,
            {"conversation_id": conversation_id, "limit": limit},
        )
        decoded_turns = [self._decode_record(turn) for turn in turns]
        recent_turns = list(reversed(decoded_turns))
        last_assistant = next((turn for turn in decoded_turns if turn.get("role") == "assistant"), None)
        last_user = next((turn for turn in decoded_turns if turn.get("role") == "user"), None)
        return ConversationMemoryContext(
            conversation_id=conversation.id,
            session_id=conversation.session_id,
            municipio_id=conversation.municipio_id,
            municipio_nombre=conversation.municipio_nombre,
            last_question=last_user.get("question") if last_user else None,
            last_answer=last_assistant.get("answer") if last_assistant else None,
            last_operation=last_assistant.get("operation") if last_assistant else None,
            last_tool_name=last_assistant.get("tool_name") if last_assistant else None,
            last_metric=last_assistant.get("metric") if last_assistant else None,
            last_metric_label=last_assistant.get("metric_label") if last_assistant else None,
            last_year=last_assistant.get("year") if last_assistant else None,
            last_start_year=last_assistant.get("start_year") if last_assistant else None,
            last_end_year=last_assistant.get("end_year") if last_assistant else None,
            last_party=last_assistant.get("party") if last_assistant else None,
            last_election_type=last_assistant.get("election_type") if last_assistant else None,
            last_election_year=last_assistant.get("election_year") if last_assistant else None,
            last_sections=last_assistant.get("sections") if last_assistant else [],
            last_result_rows=last_assistant.get("result_rows") if last_assistant else [],
            last_summary=last_assistant.get("summary") if last_assistant else {},
            last_chart_spec=last_assistant.get("chart_spec") if last_assistant else None,
            last_methodology_plain=last_assistant.get("methodology_plain") if last_assistant else None,
            last_caveats=last_assistant.get("caveats") if last_assistant else [],
            last_suggested_followups=last_assistant.get("suggested_followups") if last_assistant else [],
            recent_turns=recent_turns,
        )

    def clear_conversation(self, conversation_id: str) -> None:
        self._execute("UPDATE core.agent_conversations SET status = 'cleared', updated_at = CURRENT_TIMESTAMP WHERE id = :id", {"id": conversation_id})
        self.session.commit()

    def delete_inactive(self, days: int = 30) -> int:
        sql = (
            "DELETE FROM core.agent_conversations WHERE last_active_at < datetime('now', :interval)"
            if self._dialect == "sqlite"
            else "DELETE FROM core.agent_conversations WHERE last_active_at < now() - (:days * INTERVAL '1 day')"
        )
        params = {"interval": f"-{int(days)} days"} if self._dialect == "sqlite" else {"days": int(days)}
        result = self._execute(sql, params)
        self.session.commit()
        return int(result.rowcount or 0)

    def _append_turn(self, conversation_id: str, role: str, **values: Any) -> TurnRecord:
        turn_index = self._next_turn_index(conversation_id)
        turn_id = str(uuid.uuid4())
        payload = {
            "id": turn_id,
            "conversation_id": conversation_id,
            "turn_index": turn_index,
            "role": role,
            **values,
        }
        defaults = {
            "question": None,
            "answer": None,
            "operation": None,
            "tool_name": None,
            "provider": None,
            "model": None,
            "complexity": None,
            "metric": None,
            "metric_label": None,
            "municipio_id": None,
            "municipio_nombre": None,
            "year": None,
            "start_year": None,
            "end_year": None,
            "party": None,
            "election_type": None,
            "election_year": None,
            "sections": [],
            "result_rows": [],
            "summary": {},
            "chart_spec": None,
            "methodology_plain": None,
            "caveats": [],
            "suggested_followups": [],
            "tool_args": {},
            "tool_result_status": None,
            "guard_result": {},
            "latency_ms": None,
        }
        for key, value in defaults.items():
            payload.setdefault(key, value)
        for key in ("sections", "result_rows", "summary", "chart_spec", "caveats", "suggested_followups", "tool_args", "guard_result"):
            payload[key] = self._json_param(payload.get(key, [] if key in {"sections", "result_rows", "caveats", "suggested_followups"} else {}))
        self._execute(
            """
            INSERT INTO core.agent_turns (
                id, conversation_id, turn_index, role, question, answer, operation, tool_name,
                provider, model, complexity, metric, metric_label, municipio_id, municipio_nombre,
                year, start_year, end_year, party, election_type, election_year, sections,
                result_rows, summary, chart_spec, methodology_plain, caveats, suggested_followups,
                tool_args, tool_result_status, guard_result, latency_ms
            ) VALUES (
                :id, :conversation_id, :turn_index, :role, :question, :answer, :operation, :tool_name,
                :provider, :model, :complexity, :metric, :metric_label, :municipio_id, :municipio_nombre,
                :year, :start_year, :end_year, :party, :election_type, :election_year, :sections,
                :result_rows, :summary, :chart_spec, :methodology_plain, :caveats, :suggested_followups,
                :tool_args, :tool_result_status, :guard_result, :latency_ms
            )
            """,
            payload,
        )
        self._execute(
            "UPDATE core.agent_conversations SET updated_at = CURRENT_TIMESTAMP, last_active_at = CURRENT_TIMESTAMP WHERE id = :id",
            {"id": conversation_id},
        )
        self.session.commit()
        return TurnRecord.model_validate(self._decode_record(self._fetch_one("SELECT * FROM core.agent_turns WHERE id = :id", {"id": turn_id})))

    def _next_turn_index(self, conversation_id: str) -> int:
        row = self._fetch_one("SELECT COALESCE(MAX(turn_index), 0) + 1 AS next_index FROM core.agent_turns WHERE conversation_id = :conversation_id", {"conversation_id": conversation_id})
        return int(row["next_index"] if row else 1)

    def _fetch_one(self, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
        try:
            row = self.session.execute(text(sql), params).mappings().first()
            return dict(row) if row else None
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.warning("persistent_conversation_store_sql_error", exc_info=False)
            self._raise_memory_error(exc)

    def _fetch_all(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            return [dict(row) for row in self.session.execute(text(sql), params).mappings().all()]
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.warning("persistent_conversation_store_sql_error", exc_info=False)
            self._raise_memory_error(exc)

    def _execute(self, sql: str, params: dict[str, Any]):
        try:
            return self.session.execute(text(sql), params)
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.warning("persistent_conversation_store_sql_error", exc_info=False)
            self._raise_memory_error(exc)

    def _raise_memory_error(self, exc: SQLAlchemyError) -> None:
        text_value = f"{exc.__class__.__name__} {getattr(exc, 'orig', '')} {exc}"
        if "UndefinedTable" not in text_value and "does not exist" not in text_value and "no such table" not in text_value:
            raise PersistentMemoryUnavailable(
                "Persistent memory SQL failure.\n\n"
                "Check the database connection and persistent memory schema before enabling ASK_USE_LLM_PLANNER."
            ) from exc
        raise PersistentMemoryUnavailable(
            "Persistent memory tables missing.\n\n"
            "Run memory migration before enabling ASK_USE_LLM_PLANNER:\n\n"
            "python scripts/apply_agent_memory_migration.py"
        ) from exc

    def _json_param(self, value: Any) -> Any:
        safe = self._jsonable(value)
        if self._dialect == "sqlite":
            return json.dumps(safe, ensure_ascii=False)
        try:
            from psycopg.types.json import Jsonb

            return Jsonb(safe)
        except Exception:
            return json.dumps(safe, ensure_ascii=False)

    def _decode_record(self, row: dict[str, Any]) -> dict[str, Any]:
        decoded = dict(row)
        for key in ("metadata", "sections", "result_rows", "summary", "chart_spec", "caveats", "suggested_followups", "tool_args", "guard_result"):
            if key in decoded:
                decoded[key] = self._decode_json(decoded[key])
        for key in ("id", "conversation_id"):
            if key in decoded and decoded[key] is not None:
                decoded[key] = str(decoded[key])
        return decoded

    def _decode_json(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def _jsonable(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(key): self._jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._jsonable(item) for item in value]
        return str(value)

    def _safe_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        blocked = {"api_key", "gemini_api_key", "openai_api_key", "raw", "sql", "traceback", "exception", "prompt"}
        return {key: value for key, value in metadata.items() if key.lower() not in blocked}

    def _sections_from_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {"section_id": row.get("section_id"), "section_name": row.get("section_name"), "value": row.get("value"), "value_label": row.get("value_label")}
            for row in rows
            if row.get("section_id") or row.get("section_name")
        ]

    def _int_or_none(self, value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None


def conversation_memory_to_state(context: ConversationMemoryContext):
    from app.ask.conversation.conversation_state import ConversationSection, ConversationState, ElectionContext, LastAnswerContext, MunicipalityContext

    state = ConversationState(conversationId=context.session_id, municipality=context.municipio_id)
    state.lastQuestion = context.last_question
    state.lastAnswer = context.last_answer
    state.lastTool = context.last_tool_name
    state.last_tool_name = context.last_tool_name
    state.last_operation = context.last_operation
    state.lastResultType = context.last_operation
    state.lastMetric = context.last_metric
    state.lastYear = context.last_year
    state.last_start_year = context.last_start_year
    state.last_end_year = context.last_end_year
    state.lastParty = context.last_party
    state.last_party = context.last_party
    state.last_rows = list(context.last_result_rows)
    state.lastResultRows = list(context.last_result_rows)
    state.lastResult = {"rows": context.last_result_rows, "summary": context.last_summary}
    state.last_chart_spec = context.last_chart_spec
    state.lastMethodology = context.last_methodology_plain
    state.lastCaveats = list(context.last_caveats)
    state.lastSections = [
        ConversationSection(
            sectionId=str(section.get("section_id") or section.get("sectionId") or section.get("section_name")),
            sectionName=str(section.get("section_name") or section.get("sectionName") or section.get("section_id")),
            value=section.get("value") if isinstance(section.get("value"), (int, float)) else None,
            valueLabel=section.get("value_label") or section.get("valueLabel"),
        )
        for section in context.last_sections
    ]
    if state.lastSections:
        state.lastSection = state.lastSections[0]
    if context.last_answer or context.last_question:
        state.lastAnswerContext = LastAnswerContext(
            question=context.last_question or "",
            answerSummary=(context.last_answer or "")[:240],
            operation=context.last_operation or "unknown",
            tool=context.last_tool_name,
            metric=context.last_metric,
            metricLabel=context.last_metric_label,
            municipality=MunicipalityContext(id=context.municipio_id, name=context.municipio_nombre),
            year=context.last_year,
            startYear=context.last_start_year,
            endYear=context.last_end_year,
            election=ElectionContext(type=context.last_election_type, year=context.last_election_year) if context.last_election_type or context.last_election_year else None,
            sections=state.lastSections,
            resultRows=context.last_result_rows,
            chartSpec=context.last_chart_spec,
            methodologyPlain=context.last_methodology_plain,
            caveats=context.last_caveats,
            party=context.last_party,
        )
    return state
