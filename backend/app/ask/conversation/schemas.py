from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationRecord(BaseModel):
    id: str
    user_id: str | None = None
    session_id: str
    municipio_id: str = "29070"
    municipio_nombre: str = "Mijas"
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
    last_active_at: datetime | str | None = None
    status: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TurnRecord(BaseModel):
    id: str
    conversation_id: str
    turn_index: int
    role: str
    question: str | None = None
    answer: str | None = None
    operation: str | None = None
    tool_name: str | None = None
    provider: str | None = None
    model: str | None = None
    complexity: str | None = None
    metric: str | None = None
    metric_label: str | None = None
    municipio_id: str | None = None
    municipio_nombre: str | None = None
    year: int | None = None
    start_year: int | None = None
    end_year: int | None = None
    party: str | None = None
    election_type: str | None = None
    election_year: int | None = None
    sections: list[dict[str, Any]] = Field(default_factory=list)
    result_rows: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    chart_spec: dict[str, Any] | None = None
    methodology_plain: str | None = None
    caveats: list[str] = Field(default_factory=list)
    suggested_followups: list[str] = Field(default_factory=list)
    tool_args: dict[str, Any] = Field(default_factory=dict)
    tool_result_status: str | None = None
    guard_result: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = None
    created_at: datetime | str | None = None


class ConversationMemoryContext(BaseModel):
    conversation_id: str
    session_id: str
    municipio_id: str = "29070"
    municipio_nombre: str = "Mijas"
    last_question: str | None = None
    last_answer: str | None = None
    last_operation: str | None = None
    last_tool_name: str | None = None
    last_metric: str | None = None
    last_metric_label: str | None = None
    last_year: int | None = None
    last_start_year: int | None = None
    last_end_year: int | None = None
    last_party: str | None = None
    last_election_type: str | None = None
    last_election_year: int | None = None
    last_sections: list[dict[str, Any]] = Field(default_factory=list)
    last_result_rows: list[dict[str, Any]] = Field(default_factory=list)
    last_summary: dict[str, Any] = Field(default_factory=dict)
    last_chart_spec: dict[str, Any] | None = None
    last_methodology_plain: str | None = None
    last_caveats: list[str] = Field(default_factory=list)
    last_suggested_followups: list[str] = Field(default_factory=list)
    recent_turns: list[dict[str, Any]] = Field(default_factory=list)
