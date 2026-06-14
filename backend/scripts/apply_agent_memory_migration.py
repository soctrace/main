from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ask.diagnostics import check_memory_tables
from app.core.database import SessionLocal


MIGRATION_NAME = "030_agent_conversation_memory.sql"


def migration_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    existing = list(root.rglob(MIGRATION_NAME))
    if existing:
        return existing[0]
    path = root / "sql" / "core" / MIGRATION_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_migration_sql(), encoding="utf-8")
    return path


def main() -> int:
    session = SessionLocal()
    try:
        before = check_memory_tables(session)
        if all(before.values()):
            print("already exists")
            return 0
        path = migration_path()
        sql = path.read_text(encoding="utf-8")
        with session.connection().engine.begin() as connection:
            for statement in _split_sql(sql):
                connection.exec_driver_sql(statement)
        after = check_memory_tables(session)
        if all(after.values()):
            print("migration applied")
            return 0
        print(f"migration incomplete: {after}")
        return 1
    finally:
        session.close()


def _migration_sql() -> str:
    return """
CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.agent_conversations (
    id UUID PRIMARY KEY,
    user_id TEXT NULL,
    session_id TEXT NOT NULL,
    municipio_id TEXT NOT NULL DEFAULT '29070',
    municipio_nombre TEXT NOT NULL DEFAULT 'Mijas',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'active',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_agent_conversations_session_id ON core.agent_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_user_id ON core.agent_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_last_active ON core.agent_conversations(last_active_at);

CREATE TABLE IF NOT EXISTS core.agent_turns (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES core.agent_conversations(id) ON DELETE CASCADE,
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
    sections JSONB NOT NULL DEFAULT '[]'::jsonb,
    result_rows JSONB NOT NULL DEFAULT '[]'::jsonb,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    chart_spec JSONB NULL,
    methodology_plain TEXT NULL,
    caveats JSONB NOT NULL DEFAULT '[]'::jsonb,
    suggested_followups JSONB NOT NULL DEFAULT '[]'::jsonb,
    tool_args JSONB NOT NULL DEFAULT '{}'::jsonb,
    tool_result_status TEXT NULL,
    guard_result JSONB NOT NULL DEFAULT '{}'::jsonb,
    latency_ms INTEGER NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_agent_turns_conversation_index UNIQUE(conversation_id, turn_index),
    CONSTRAINT chk_agent_turns_role CHECK(role IN ('user', 'assistant', 'system', 'tool'))
);

CREATE INDEX IF NOT EXISTS idx_agent_turns_conversation_created ON core.agent_turns(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_turns_metric ON core.agent_turns(metric);
CREATE INDEX IF NOT EXISTS idx_agent_turns_tool_name ON core.agent_turns(tool_name);
CREATE INDEX IF NOT EXISTS idx_agent_turns_sections_gin ON core.agent_turns USING GIN (sections);
CREATE INDEX IF NOT EXISTS idx_agent_turns_result_rows_gin ON core.agent_turns USING GIN (result_rows);
""".strip()


def _split_sql(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    previous = ""
    for char in sql:
        if char == "'" and previous != "\\":
            in_single_quote = not in_single_quote
        if char == ";" and not in_single_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        previous = char
    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return statements


if __name__ == "__main__":
    raise SystemExit(main())
