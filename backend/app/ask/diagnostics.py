from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ask.semantic_layer import SemanticCatalog
from app.ask.sql import SqlValidator
from app.ask.tools_v2.registry import get_llm_tool_schemas
from app.core.config import Settings, get_settings


MEMORY_TABLES = ("core.agent_conversations", "core.agent_turns")


def check_gemini_sdk() -> tuple[bool, str | None]:
    try:
        from google import genai  # noqa: F401

        return True, None
    except Exception as exc:
        return False, (
            "Gemini SDK missing.\n\n"
            "Run:\n\n"
            "pip install google-genai\n\n"
            "Then restart backend."
            f"\n\nOriginal error: {exc}"
        )


def check_memory_tables(session: Session) -> dict[str, bool]:
    result: dict[str, bool] = {}
    dialect = session.bind.dialect.name if session.bind is not None else "postgresql"
    for relation in MEMORY_TABLES:
        if dialect == "sqlite":
            schema, table = relation.split(".", 1)
            row = session.execute(
                text("SELECT 1 FROM core.sqlite_master WHERE type = 'table' AND name = :table"),
                {"table": table},
            ).first()
        else:
            row = session.execute(text("SELECT to_regclass(:relation)"), {"relation": relation}).first()
        result[relation] = bool(row and row[0])
    return result


def check_tool_layer() -> tuple[bool, str | None]:
    try:
        catalog = SemanticCatalog()
        SqlValidator(catalog.approved_relations)
        schemas = get_llm_tool_schemas(include_beta=True)
        return bool(schemas), None if schemas else "No Tool Layer v2 schemas are exported."
    except Exception as exc:
        return False, str(exc)


def ask_llm_health(session: Session | None = None, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    gemini_sdk, gemini_error = check_gemini_sdk()
    memory_tables: bool | None = None
    memory_table_details: dict[str, bool] = {}
    issues: list[str] = []

    if settings.llm_provider.strip().lower() == "gemini" and not gemini_sdk:
        issues.append("gemini_sdk_missing")
    if settings.llm_provider.strip().lower() == "gemini" and not bool(settings.gemini_api_key):
        issues.append("gemini_api_key_missing")

    if session is not None:
        try:
            memory_table_details = check_memory_tables(session)
            memory_tables = all(memory_table_details.values())
            if not memory_tables:
                issues.append("persistent_memory_tables_missing")
        except Exception as exc:
            session.rollback()
            memory_tables = False
            memory_table_details = {table: False for table in MEMORY_TABLES}
            issues.append(f"persistent_memory_check_failed: {exc}")

    tool_layer, tool_error = check_tool_layer()
    if not tool_layer:
        issues.append("tool_layer_unavailable")

    status = "healthy" if not issues else "degraded"
    payload: dict[str, Any] = {
        "provider": settings.llm_provider,
        "planner_enabled": bool(settings.ask_use_llm_planner),
        "gemini_sdk": gemini_sdk,
        "api_key_loaded": bool(settings.gemini_api_key),
        "memory_tables": memory_tables,
        "memory_table_details": memory_table_details,
        "tool_layer": tool_layer,
        "status": status,
        "issues": issues,
    }
    if gemini_error and not gemini_sdk:
        payload["gemini_error"] = gemini_error
    if tool_error:
        payload["tool_layer_error"] = tool_error
    return payload


def diagnostics_banner(session: Session | None = None, settings: Settings | None = None) -> str:
    health = ask_llm_health(session=session, settings=settings)

    def ok(value: Any) -> str:
        if value is True:
            return "OK"
        if value is False:
            return "MISSING"
        return "UNKNOWN"

    return "\n".join(
        [
            "========================",
            "SOC TRACE AI AGENT",
            "========================",
            "",
            f"Provider: {health['provider']}",
            f"Planner: {'enabled' if health['planner_enabled'] else 'disabled'}",
            f"Gemini SDK: {ok(health['gemini_sdk'])}",
            f"Memory tables: {ok(health['memory_tables'])}",
            f"Tool Layer: {ok(health['tool_layer'])}",
            "",
            "========================",
        ]
    )
