import re

import pytest

from app.ask.participation_trend import resolve_participation_trend
from app.ask.sql import QueryExecutor
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


ROWS = [
    {
        "election_year": 2019,
        "election_type": "MUNICIPALES",
        "election_id": "MUN_2019",
        "election_label": "Municipales 2019",
        "participation_pct": 52.55,
        "total_votes": 22300,
        "census": 42436,
    },
    {
        "election_year": 2023,
        "election_type": "MUNICIPALES",
        "election_id": "MUN_2023",
        "election_label": "Municipales 2023",
        "participation_pct": 51.82,
        "total_votes": 24600,
        "census": 47472,
    },
]


class RecordingQueryExecutor:
    def __init__(self, rows=None) -> None:
        self.rows = list(ROWS if rows is None else rows)
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute(self, sql: str, parameters: dict[str, object]):
        self.calls.append((sql, parameters))
        return [dict(row) for row in self.rows]


@pytest.mark.parametrize(
    ("question", "start_year", "end_year"),
    [
        ("¿Cómo ha evolucionado la participación desde 2019?", 2019, None),
        ("Evolución de la participación entre 2019 y 2023", 2019, 2023),
        ("Participación electoral por años", None, None),
    ],
)
def test_municipality_participation_trend_uses_election_year_chronologically(
    question: str,
    start_year: int | None,
    end_year: int | None,
) -> None:
    executor = RecordingQueryExecutor()

    resolution = resolve_participation_trend(AskRequest(question=question), executor)  # type: ignore[arg-type]

    assert resolution is not None
    sql, parameters = executor.calls[0]
    assert "marts.agent_electoral_summary" in sql
    assert "summary.election_year" in sql
    assert not re.search(r"\bsummary\.year\b", sql)
    assert "ORDER BY summary.election_year" in sql
    assert "rank_sections" not in sql
    assert parameters["municipio_id"] == "29070"
    assert parameters.get("start_year") == start_year
    assert parameters.get("end_year") == end_year
    assert resolution.response.resultType == "time_series"
    assert resolution.response.data["territorial_scope"] == "municipality"
    assert resolution.response.data["rows"] == ROWS
    assert [row["election_year"] for row in resolution.response.data["rows"]] == [2019, 2023]
    assert resolution.response.data["direction"] == "disminuyó"


def test_section_participation_trend_uses_parameterized_section_filter() -> None:
    executor = RecordingQueryExecutor()

    resolution = resolve_participation_trend(
        AskRequest(question="Participación en la sección 18 desde 2019"),
        executor,
    )  # type: ignore[arg-type]

    assert resolution is not None
    sql, parameters = executor.calls[0]
    assert "section_number = :section_number" in sql
    assert parameters["section_number"] == "18"
    assert resolution.tool_arguments["section"] == "18"
    assert resolution.response.data["territorial_scope"] == "section"
    assert resolution.response.data["requested_section_id"] == "18"
    assert resolution.response.data["rows"] == ROWS


def test_no_data_is_explicit_and_does_not_fall_back_to_ranking() -> None:
    executor = RecordingQueryExecutor(rows=[])

    resolution = resolve_participation_trend(
        AskRequest(question="¿Cómo ha evolucionado la participación desde 2099?"),
        executor,
    )  # type: ignore[arg-type]

    assert resolution is not None
    assert resolution.response.data["rows"] == []
    assert resolution.response.data["tool"] == "participation_trend"
    assert "No hay datos" in resolution.response.answer


def test_single_year_participation_query_remains_unchanged() -> None:
    executor = RecordingQueryExecutor()

    resolution = resolve_participation_trend(
        AskRequest(question="¿Cuál fue la participación en 2023?"),
        executor,
    )  # type: ignore[arg-type]

    assert resolution is None
    assert executor.calls == []


def test_clean_head_participation_trend_returns_database_rows() -> None:
    with SessionLocal() as session:
        resolution = resolve_participation_trend(
            AskRequest(question="¿Cómo ha evolucionado la participación desde 2019?"),
            QueryExecutor(session),
        )

    assert resolution is not None
    rows = resolution.response.data["rows"]
    assert rows
    assert [row["election_year"] for row in rows] == sorted(
        row["election_year"] for row in rows
    )
    assert resolution.response.data["territorial_scope"] == "municipality"
    assert resolution.response.resultType == "time_series"
