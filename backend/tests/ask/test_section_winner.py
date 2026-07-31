import logging

import pytest

from app.ask.section_winner import resolve_section_winner
from app.ask.sql.query_executor import QueryExecutor
from app.ask.tools_v2 import ToolResult
from app.ask.tools_v2.schemas import SectionProfileInput
from app.ask.tools_v2.sql_builders import ToolSqlBuilders
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


class FakeToolExecutor:
    def __init__(self, *, returned_section: str | None = None) -> None:
        self.returned_section = returned_section
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute_sync(self, tool_name, arguments, context):
        self.calls.append((tool_name, arguments))
        requested = str(arguments["section"])
        effective = self.returned_section or f"2907001{int(requested):03d}"
        visible = int(effective[-3:])
        return ToolResult(
            tool_name="section_profile",
            operation="section_profile",
            status="ok",
            rows=[
                {
                    "section_id": effective,
                    "section_name": f"Sección {visible:02d} · Fixture",
                    "election_year": int(arguments["year"]),
                    "winner_party": "FIXTURE PARTY",
                }
            ],
            sources=["marts.agent_electoral_summary"],
        )


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("¿Cuál fue el partido ganador en la sección 18 en las elecciones municipales de 2023?", "18"),
        ("¿Qué partido ganó en la sección 7 en las municipales de 2023?", "7"),
        ("Ganador electoral de la sección 23 en 2023", "23"),
        ("En la sección nº37, ¿quién ganó las municipales de 2023?", "37"),
        ("Ganador electoral de la sección 01 en 2023", "1"),
        ("Ganador electoral de s18 en 2023", "18"),
        ("Ganador electoral de sec 23 en 2023", "23"),
    ],
)
def test_honors_requested_section_end_to_end(question: str, expected: str) -> None:
    executor = FakeToolExecutor()
    payload = AskRequest(question=question, activeMunicipality="29070")

    resolution = resolve_section_winner(payload, executor)  # type: ignore[arg-type]

    assert resolution is not None
    assert executor.calls == [
        (
            "section_profile",
            {
                "municipio_id": "29070",
                "section": expected,
                "year": 2023,
                "include_domains": ["electoral"],
            },
        )
    ]
    assert resolution.response.data["requested_section_id"] == expected
    assert resolution.response.data["effective_section_id"] == expected
    assert resolution.response.data["response_section_id"] == expected
    assert resolution.response.data["territorial_match"] is True
    assert f"Sección {int(expected):02d}" in resolution.response.answer


@pytest.mark.parametrize(
    "question",
    [
        "¿Qué sección tuvo mayor densidad en 2025?",
        "¿Qué partido ganó las elecciones municipales de 2023 en Mijas?",
        "Compara los resultados de las secciones 10 y 23",
    ],
)
def test_does_not_capture_out_of_scope_queries(question: str) -> None:
    executor = FakeToolExecutor()

    assert resolve_section_winner(AskRequest(question=question), executor) is None  # type: ignore[arg-type]
    assert executor.calls == []


def test_rejects_a_row_from_another_section(caplog: pytest.LogCaptureFixture) -> None:
    executor = FakeToolExecutor(returned_section="2907001001")
    payload = AskRequest(
        question="¿Cuál fue el partido ganador en la sección 18 en las elecciones municipales de 2023?"
    )

    with caplog.at_level(logging.INFO, logger="app.ask.section_winner"):
        resolution = resolve_section_winner(payload, executor)  # type: ignore[arg-type]

    assert resolution is not None
    assert resolution.response.data["requested_section_id"] == "18"
    assert resolution.response.data["effective_section_id"] is None
    assert resolution.response.data["response_section_id"] is None
    assert resolution.response.data["territorial_match"] is False
    assert "Sección 01" not in resolution.response.answer
    assert "territorial_match" in caplog.records[-1].__dict__
    assert caplog.records[-1].territorial_match is False


def test_structured_observability_reports_matching_section(caplog: pytest.LogCaptureFixture) -> None:
    payload = AskRequest(
        question="¿Cuál fue el partido ganador en la sección 18 en las elecciones municipales de 2023?"
    )

    with caplog.at_level(logging.INFO, logger="app.ask.section_winner"):
        resolution = resolve_section_winner(payload, FakeToolExecutor())  # type: ignore[arg-type]

    assert resolution is not None
    record = caplog.records[-1]
    assert record.event == "section_winner_resolution"
    assert record.requested_section_id == "18"
    assert record.effective_section_id == "18"
    assert record.election_type == "municipal"
    assert record.election_year == 2023
    assert record.tool_name == "section_profile"
    assert record.row_count == 1
    assert record.territorial_match is True


@pytest.mark.parametrize(
    ("section", "expected_parameter"),
    [("18", "18"), ("07", "07"), ("7", "07"), ("37", "37")],
)
def test_section_profile_binds_visible_section_number_as_database_text(
    section: str,
    expected_parameter: str,
) -> None:
    built = ToolSqlBuilders().section_profile(
        SectionProfileInput(municipio_id="29070", section=section, year=2023)
    )

    assert "section_number = :section_number" in built.sql
    assert "CAST(section_number" not in built.sql
    assert built.parameters == {"section_number": expected_parameter}
    assert isinstance(built.parameters["section_number"], str)


class RecordingSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute(self, statement, parameters=None):
        self.calls.append((str(statement), parameters or {}))
        if len(self.calls) == 1:
            return None
        return RecordingResult()

    def rollback(self) -> None:
        raise AssertionError("The query should not fail")


class RecordingResult:
    def mappings(self):
        return self

    def all(self):
        return []


def test_query_executor_passes_text_section_parameter_to_sqlalchemy() -> None:
    session = RecordingSession()
    QueryExecutor(session).execute(  # type: ignore[arg-type]
        "SELECT section_id FROM marts.agent_section_lookup WHERE section_number = :section_number",
        {"section_number": "18"},
    )

    assert session.calls[-1][1] == {"section_number": "18"}
    assert isinstance(session.calls[-1][1]["section_number"], str)


def test_multiple_requested_sections_are_not_collapsed_to_one() -> None:
    executor = FakeToolExecutor()
    payload = AskRequest(question="Compara los ganadores electorales de las secciones 18 y 23 en 2023")

    assert resolve_section_winner(payload, executor) is None  # type: ignore[arg-type]
    assert executor.calls == []


def test_explicit_year_resolves_once_without_contradictory_profile_predicate() -> None:
    built = ToolSqlBuilders().section_profile(
        SectionProfileInput(municipio_id="29070", section="18", year=2023)
    )

    assert "COALESCE(MAX(year) FILTER (WHERE year = 2023), MAX(year)) AS year" in built.sql
    assert "COALESCE(MAX(election_year) FILTER (WHERE election_year = 2023), MAX(election_year)) AS election_year" in built.sql
    assert "profile.year = 2023" not in built.sql
    assert built.sql.count("profile.year = latest_profile.year") == 1


def test_missing_explicit_year_uses_latest_available_year_once() -> None:
    built = ToolSqlBuilders().section_profile(
        SectionProfileInput(municipio_id="29070", section="18")
    )

    assert "SELECT MAX(year) AS year FROM marts.agent_section_profile" in built.sql
    assert "SELECT MAX(election_year) AS election_year FROM marts.agent_electoral_summary" in built.sql
    assert "FILTER (WHERE year" not in built.sql
    assert "FILTER (WHERE election_year" not in built.sql


def test_requested_year_without_profile_data_falls_back_to_canonical_latest_year() -> None:
    built = ToolSqlBuilders().section_profile(
        SectionProfileInput(municipio_id="29070", section="18", year=1900)
    )

    with SessionLocal() as session:
        rows = QueryExecutor(session).execute(built.sql, built.parameters)

    assert len(rows) == 1
    assert rows[0]["section_id"] == "2907001018"
    assert rows[0]["year"] != 1900


@pytest.mark.parametrize(
    ("section", "winner"),
    [("7", "PP"), ("18", "PSOE"), ("23", "PP"), ("37", "PSOE")],
)
def test_clean_head_section_profile_returns_municipal_2023_winner(
    section: str,
    winner: str,
) -> None:
    built = ToolSqlBuilders().section_profile(
        SectionProfileInput(municipio_id="29070", section=section, year=2023)
    )

    with SessionLocal() as session:
        rows = QueryExecutor(session).execute(built.sql, built.parameters)

    assert len(rows) == 1
    assert rows[0]["election_year"] == 2023
    assert rows[0]["winner_party"] == winner
    assert str(int(rows[0]["section_id"][-3:])) == str(int(section))
