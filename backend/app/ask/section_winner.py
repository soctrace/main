from dataclasses import dataclass
import logging
import re
import unicodedata

from app.ask.section_reference import detect_section_references
from app.ask.tools_v2 import ToolContext, ToolExecutorV2
from app.schemas.ask import AskRequest, AskResponse


logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(character) != "Mn"
    )


def _visible_section_id(section_id: str) -> str | None:
    if not section_id.isdigit():
        return None
    if len(section_id) == 10:
        return str(int(section_id[-3:]))
    return str(int(section_id))


def _territorial_match(requested: str, effective: str) -> bool:
    if requested == effective:
        return True
    requested_visible = _visible_section_id(requested)
    effective_visible = _visible_section_id(effective)
    return requested_visible is not None and requested_visible == effective_visible


@dataclass(frozen=True, slots=True)
class SectionWinnerResolution:
    response: AskResponse
    tool_name: str
    tool_arguments: dict[str, object]


def resolve_section_winner(
    payload: AskRequest,
    tool_executor: ToolExecutorV2,
) -> SectionWinnerResolution | None:
    question = payload.question or ""
    text = _normalize(question)
    detection = detect_section_references(question)
    if detection.selected_section_id is None:
        return None
    if not re.search(r"\b(ganador|gano|gana|quien gano|que partido gano)\b", text):
        return None
    if not re.search(r"\b(eleccion|elecciones|electoral|municipal|municipales)\b", text):
        return None

    year_match = re.search(r"\b(20\d{2})\b", text)
    election_year = int(year_match.group(1)) if year_match else payload.activeYear
    if election_year is None:
        return None

    requested_section_id = detection.selected_section_id
    tool_arguments: dict[str, object] = {
        "municipio_id": payload.activeMunicipality or "29070",
        "section": requested_section_id,
        "year": election_year,
        "include_domains": ["electoral"],
    }
    result = tool_executor.execute_sync(
        "section_profile",
        tool_arguments,
        ToolContext(
            municipio_id=payload.activeMunicipality or "29070",
            municipio_nombre="Mijas" if (payload.activeMunicipality or "29070") == "29070" else None,
            active_year=election_year,
            conversation_id=payload.conversationId,
        ),
    )

    matching_rows = [
        row
        for row in result.rows
        if row.get("section_id") is not None
        and _territorial_match(requested_section_id, str(row["section_id"]))
        and row.get("election_year") == election_year
    ]
    row = matching_rows[0] if len(matching_rows) == 1 else None
    effective_section_id = _visible_section_id(str(row["section_id"])) if row else None
    territorial_match = row is not None and effective_section_id == _visible_section_id(requested_section_id)
    logger.info(
        "section_winner_resolution",
        extra={
            "event": "section_winner_resolution",
            "requested_section_id": requested_section_id,
            "effective_section_id": effective_section_id,
            "election_type": "municipal",
            "election_year": election_year,
            "tool_name": "section_profile",
            "row_count": len(result.rows),
            "territorial_match": territorial_match,
        },
    )

    if not territorial_match or row is None or not row.get("winner_party"):
        response = AskResponse(
            answer=(
                f"No puedo confirmar el partido ganador de la sección {requested_section_id} "
                f"en las elecciones municipales de {election_year} porque los datos recuperados "
                "no coinciden de forma inequívoca con la sección solicitada."
            ),
            confidence="low",
            data={
                "tool": "section_profile",
                "operation": "section_election_winner",
                "requested_section_id": requested_section_id,
                "effective_section_id": effective_section_id,
                "territorial_match": False,
                "rows": [],
            },
            methodology="Validación territorial estricta sobre el resumen electoral canónico por sección.",
            caveats=["No se devuelve información perteneciente a otra sección."],
            sources=result.sources,
        )
        return SectionWinnerResolution(response, "section_profile", tool_arguments)

    section_name = str(row.get("section_name") or f"Sección {requested_section_id}")
    winner_party = str(row["winner_party"])
    answer = (
        f"En {section_name}, el partido ganador en las elecciones municipales de "
        f"{election_year} fue {winner_party}."
    )
    response = AskResponse(
        answer=answer,
        confidence="high",
        resultType="entity_list",
        entities=[
            {
                "type": "section",
                "id": str(row["section_id"]),
                "name": section_name,
                "value": winner_party,
                "valueLabel": "Partido ganador",
            }
        ],
        data={
            "tool": "section_profile",
            "operation": "section_election_winner",
            "requested_section_id": requested_section_id,
            "effective_section_id": effective_section_id,
            "territorial_match": True,
            "election_type": "municipal",
            "election_year": election_year,
            "rows": [row],
        },
        methodology="Lectura del ganador observado en el resumen electoral canónico de la sección y elección solicitadas.",
        sources=result.sources,
    )
    return SectionWinnerResolution(response, "section_profile", tool_arguments)
