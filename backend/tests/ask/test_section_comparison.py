import pytest

from app.ask.section_comparison import resolve_section_comparison
from app.ask.tools_v2 import ToolResult
from app.schemas.ask import AskRequest


class ComparisonExecutor:
    def __init__(self, unavailable: set[str] | None = None) -> None:
        self.unavailable = unavailable or set()
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute_sync(self, tool_name, arguments, context):
        self.calls.append((tool_name, arguments))
        section = str(arguments["section"])
        if section in self.unavailable:
            rows = []
        else:
            rows = [
                {
                    "section_id": f"2907001{int(section):03d}",
                    "section_name": f"Sección {int(section):02d} · Fixture",
                    "election_year": int(arguments.get("year") or 2023),
                    "winner_party": f"PARTY {section}",
                }
            ]
        return ToolResult(
            tool_name="section_profile",
            operation="section_profile",
            status="ok" if rows else "empty",
            rows=rows,
            sources=["marts.agent_section_lookup", "marts.agent_electoral_summary"],
        )


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Compara los resultados electorales de las secciones 10 y 23.", ["10", "23"]),
        ("Compara las secciones 7 y 18.", ["7", "18"]),
        ("Compara las secciones 18 y 37.", ["18", "37"]),
        ("Compara las secciones 23 y 10.", ["23", "10"]),
    ],
)
def test_queries_and_returns_every_explicit_section_in_input_order(
    question: str,
    expected: list[str],
) -> None:
    executor = ComparisonExecutor()

    resolution = resolve_section_comparison(AskRequest(question=question), executor)  # type: ignore[arg-type]

    assert resolution is not None
    assert resolution.tool_arguments["sections"] == expected
    assert [call[1]["section"] for call in executor.calls] == expected
    assert resolution.response.data["requested_sections"] == expected
    assert resolution.response.data["effective_sections"] == expected
    assert resolution.response.data["response_sections"] == expected
    assert [row["requested_section_id"] for row in resolution.response.data["rows_by_section"]] == expected
    assert all(isinstance(call[1]["section"], str) for call in executor.calls)


def test_section_23_is_not_dropped_from_primary_comparison() -> None:
    executor = ComparisonExecutor()

    resolution = resolve_section_comparison(
        AskRequest(question="Compara los resultados electorales de las secciones 10 y 23."),
        executor,
    )  # type: ignore[arg-type]

    assert resolution is not None
    assert [call[1]["section"] for call in executor.calls] == ["10", "23"]
    assert "Sección 23" in resolution.response.answer


def test_duplicate_section_is_queried_once() -> None:
    executor = ComparisonExecutor()

    resolution = resolve_section_comparison(
        AskRequest(question="Compara las secciones 10 y 10."),
        executor,
    )  # type: ignore[arg-type]

    assert resolution is not None
    assert resolution.response.data["requested_sections"] == ["10"]
    assert [call[1]["section"] for call in executor.calls] == ["10"]
    assert resolution.response.data["response_sections"] == ["10"]


def test_unavailable_section_is_queried_and_reported_explicitly() -> None:
    executor = ComparisonExecutor(unavailable={"23"})

    resolution = resolve_section_comparison(
        AskRequest(question="Compara las secciones 10 y 23."),
        executor,
    )  # type: ignore[arg-type]

    assert resolution is not None
    assert [call[1]["section"] for call in executor.calls] == ["10", "23"]
    assert resolution.response.data["requested_sections"] == ["10", "23"]
    assert resolution.response.data["effective_sections"] == ["10"]
    assert resolution.response.data["response_sections"] == ["10", "23"]
    assert resolution.response.data["rows_by_section"][1]["status"] == "no_data"
    assert "Sección 23: sin datos disponibles" in resolution.response.answer


@pytest.mark.parametrize(
    "question",
    [
        "¿Qué partido ganó en la sección 18 en 2023?",
        "¿Qué partido ganó las elecciones municipales de 2023 en Mijas?",
    ],
)
def test_single_or_missing_section_behavior_is_unchanged(question: str) -> None:
    executor = ComparisonExecutor()

    assert resolve_section_comparison(AskRequest(question=question), executor) is None  # type: ignore[arg-type]
    assert executor.calls == []
