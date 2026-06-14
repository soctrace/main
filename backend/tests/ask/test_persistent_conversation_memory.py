import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ask.conversation.follow_up_resolver import FollowUpResolver
from app.ask.conversation.persistent_store import PersistentConversationStore, conversation_memory_to_state
from app.ask.rendering.answer_contract import AskRenderedAnswer
from app.ask.tools_v2.schemas import ToolResult


SQLITE_SCHEMA = """
CREATE TABLE core.agent_conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NULL,
    session_id TEXT NOT NULL,
    municipio_id TEXT NOT NULL DEFAULT '29070',
    municipio_nombre TEXT NOT NULL DEFAULT 'Mijas',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_active_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'active',
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX core.idx_agent_conversations_session_id ON agent_conversations(session_id);
CREATE INDEX core.idx_agent_conversations_user_id ON agent_conversations(user_id);
CREATE INDEX core.idx_agent_conversations_last_active ON agent_conversations(last_active_at);
CREATE TABLE core.agent_turns (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES agent_conversations(id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL,
    role TEXT NOT NULL,
    question TEXT NULL,
    answer TEXT NULL,
    operation TEXT NULL,
    tool_name TEXT NULL,
    provider TEXT NULL,
    model TEXT NULL,
    complexity TEXT NULL,
    metric TEXT NULL,
    metric_label TEXT NULL,
    municipio_id TEXT NULL,
    municipio_nombre TEXT NULL,
    year INTEGER NULL,
    start_year INTEGER NULL,
    end_year INTEGER NULL,
    party TEXT NULL,
    election_type TEXT NULL,
    election_year INTEGER NULL,
    sections TEXT NOT NULL DEFAULT '[]',
    result_rows TEXT NOT NULL DEFAULT '[]',
    summary TEXT NOT NULL DEFAULT '{}',
    chart_spec TEXT NULL,
    methodology_plain TEXT NULL,
    caveats TEXT NOT NULL DEFAULT '[]',
    suggested_followups TEXT NOT NULL DEFAULT '[]',
    tool_args TEXT NOT NULL DEFAULT '{}',
    tool_result_status TEXT NULL,
    guard_result TEXT NOT NULL DEFAULT '{}',
    latency_ms INTEGER NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(conversation_id, turn_index),
    CHECK(role IN ('user', 'assistant', 'system', 'tool'))
);
CREATE INDEX core.idx_agent_turns_conversation_created ON agent_turns(conversation_id, created_at);
CREATE INDEX core.idx_agent_turns_metric ON agent_turns(metric);
CREATE INDEX core.idx_agent_turns_tool_name ON agent_turns(tool_name);
"""


def make_session_factory():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS core")
        for statement in SQLITE_SCHEMA.strip().split(";"):
            if statement.strip():
                connection.exec_driver_sql(statement)
    return engine, sessionmaker(bind=engine, future=True)


def sample_tool_result(rows_count: int = 2) -> ToolResult:
    rows = [
        {
            "section_id": f"29070010{i:02d}",
            "section_name": f"Sección {i}",
            "value": 100 + i,
            "value_label": "menores de 30",
            "year": 2025,
        }
        for i in range(1, rows_count + 1)
    ]
    return ToolResult(
        tool_name="rank_sections",
        operation="rank_sections",
        status="ok",
        rows=rows,
        summary={"row_count": rows_count, "value_label": "menores de 30"},
        metadata={
            "municipio_id": "29070",
            "municipio_nombre": "Mijas",
            "year": 2025,
            "metric": "population_under_30",
            "metric_label": "Población menor de 30",
        },
        chart_spec={"type": "bar", "x": "section_name", "y": "value", "rows": rows[:5]},
        methodology_plain="He ordenado las secciones por población menor de 30 en 2025.",
        caveats=["Dato territorial por sección."],
        suggested_followups=["¿Y en porcentaje?"],
    )


class PersistentConversationMemoryTest(unittest.TestCase):
    def setUp(self):
        self.engine, self.Session = make_session_factory()
        self.session = self.Session()
        self.store = PersistentConversationStore(self.session)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_creates_and_reuses_conversation_from_session_id(self):
        first = self.store.get_or_create_conversation("session-a")
        second = self.store.get_or_create_conversation("session-a")

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.session_id, "session-a")

    def test_separates_different_session_ids(self):
        first = self.store.get_or_create_conversation("session-a")
        second = self.store.get_or_create_conversation("session-b")

        self.assertNotEqual(first.id, second.id)

    def test_appends_turns_and_stores_tool_metadata(self):
        conversation = self.store.get_or_create_conversation("session-a")
        user_turn = self.store.append_user_turn(conversation.id, "¿Qué secciones concentran más población joven?")
        assistant_turn = self.store.append_assistant_turn(
            conversation.id,
            "La primera es Sección 1.",
            sample_tool_result(),
            AskRenderedAnswer(answer="La primera es Sección 1.", chart_spec={"type": "bar"}),
            {"provider": "gemini", "model": "fake", "tool_args": {"metric": "population_under_30"}},
        )

        self.assertEqual(user_turn.turn_index, 1)
        self.assertEqual(assistant_turn.turn_index, 2)
        self.assertEqual(assistant_turn.tool_name, "rank_sections")
        self.assertEqual(assistant_turn.metric, "population_under_30")
        self.assertEqual(assistant_turn.year, 2025)
        self.assertEqual(len(assistant_turn.sections), 2)

    def test_context_retrieval_returns_last_fields_and_recent_turns(self):
        conversation = self.store.get_or_create_conversation("session-a")
        self.store.append_user_turn(conversation.id, "Pregunta")
        self.store.append_assistant_turn(conversation.id, "Respuesta", sample_tool_result(), None, {"provider": "gemini"})

        context = self.store.get_context(conversation.id)

        self.assertEqual(context.last_year, 2025)
        self.assertEqual(context.last_metric, "population_under_30")
        self.assertEqual(context.last_sections[0]["section_name"], "Sección 1")
        self.assertEqual(context.last_summary["row_count"], 2)
        self.assertEqual(len(context.recent_turns), 2)

    def test_followup_resolution_uses_persistent_context(self):
        conversation = self.store.get_or_create_conversation("session-a")
        self.store.append_user_turn(conversation.id, "¿Qué secciones concentran más población joven?")
        self.store.append_assistant_turn(conversation.id, "Respuesta", sample_tool_result(), None, {})
        state = conversation_memory_to_state(self.store.get_context(conversation.id))

        resolution = FollowUpResolver().resolve("¿Son datos de 2025?", state)

        self.assertIsNotNone(resolution)
        self.assertIn("Sí", resolution.answer)

    def test_reload_simulation_survives_new_store_instance(self):
        conversation = self.store.get_or_create_conversation("session-a")
        self.store.append_user_turn(conversation.id, "Pregunta")
        self.store.append_assistant_turn(conversation.id, "Respuesta", sample_tool_result(), None, {})
        self.session.close()

        new_session = self.Session()
        try:
            new_store = PersistentConversationStore(new_session)
            context = new_store.get_context(conversation.id)
            self.assertEqual(context.last_metric, "population_under_30")
            self.assertEqual(context.last_methodology_plain, "He ordenado las secciones por población menor de 30 en 2025.")
        finally:
            new_session.close()

    def test_result_row_limit_and_truncation_marker(self):
        conversation = self.store.get_or_create_conversation("session-a")
        turn = self.store.append_assistant_turn(conversation.id, "Respuesta", sample_tool_result(60), None, {})

        self.assertEqual(len(turn.result_rows), 50)
        self.assertTrue(turn.summary["rows_truncated"])
        self.assertEqual(turn.summary["rows_total"], 60)

    def test_session_privacy_by_session_id(self):
        conv_a = self.store.get_or_create_conversation("session-a")
        conv_b = self.store.get_or_create_conversation("session-b")
        self.store.append_assistant_turn(conv_a.id, "Respuesta A", sample_tool_result(), None, {})
        self.store.append_assistant_turn(conv_b.id, "Respuesta B", sample_tool_result(), None, {})

        loaded_a = self.store.get_or_create_conversation("session-a")
        context_a = self.store.get_context(loaded_a.id)

        self.assertEqual(loaded_a.id, conv_a.id)
        self.assertNotEqual(loaded_a.id, conv_b.id)
        self.assertEqual(context_a.last_answer, "Respuesta A")


if __name__ == "__main__":
    unittest.main()
