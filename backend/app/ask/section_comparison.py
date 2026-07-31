from dataclasses import dataclass
import re
import unicodedata

from app.ask.section_reference import detect_section_references
from app.ask.section_winner import _territorial_match, _visible_section_id
from app.ask.tools_v2 import ToolContext, ToolExecutorV2
from app.schemas.ask import AskRequest, AskResponse


def _normalize(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(character) != "Mn"
    )


@dataclass(frozen=True, slots=True)
class SectionComparisonResolution:
    response: AskResponse
    tool_name: str
    tool_arguments: dict[str, object]


def resolve_section_comparison(
    payload: AskRequest,
    tool_executor: ToolExecutorV2,
) -> SectionComparisonResolution | None:
    question = payload.question or ""
    text = _normalize(question)
    if not re.search(r"\b(compara|comparar|comparacion)\b", text):
        return None
    if not re.search(r"\bsecciones\b.*\d{1,2}\s*(?:,|y|e)\s*\d{1,2}\b", text):
        return None

    detection = detect_section_references(question)
    requested_sections = list(detection.section_ids)
    if not requested_sections:
        return None

    year_match = re.search(r"\b(20\d{2})\b", text)
    requested_year = int(year_match.group(1)) if year_match else payload.activeYear
    municipality_id = payload.activeMunicipality or "29070"
    rows_by_section: list[dict[str, object]] = []
    sources: list[str] = []
    effective_sections: list[str] = []

    for section_id in requested_sections:
        arguments: dict[str, object] = {
            "municipio_id": municipality_id,
            "section": section_id,
            "year": requested_year,
            "include_domains": ["electoral"],
        }
        result = tool_executor.execute_sync(
            "section_profile",
            arguments,
            ToolContext(
                municipio_id=municipality_id,
                municipio_nombre="Mijas" if municipality_id == "29070" else None,
                active_year=requested_year,
                conversation_id=payload.conversationId,
            ),
        )
        for source in result.sources:
            if source not in sources:
                sources.append(source)
        matching_rows = [
            row
            for row in result.rows
            if row.get("section_id") is not None
            and _territorial_match(section_id, str(row["section_id"]))
        ]
        row = matching_rows[0] if len(matching_rows) == 1 else None
        effective_section = _visible_section_id(str(row["section_id"])) if row else None
        if row is None or effective_section is None:
            rows_by_section.append(
                {
                    "requested_section_id": section_id,
                    "effective_section_id": None,
                    "response_section_id": section_id,
                    "status": "no_data",
                    "row": None,
                }
            )
            continue
        effective_sections.append(effective_section)
        rows_by_section.append(
            {
                "requested_section_id": section_id,
                "effective_section_id": effective_section,
                "response_section_id": effective_section,
                "status": "ok",
                "row": row,
            }
        )

    answer_parts: list[str] = []
    entities: list[dict[str, object]] = []
    for item in rows_by_section:
        requested = str(item["requested_section_id"])
        row = item["row"]
        if not isinstance(row, dict):
            answer_parts.append(f"Sección {int(requested):02d}: sin datos disponibles.")
            continue
        section_name = str(row.get("section_name") or f"Sección {int(requested):02d}")
        winner = row.get("winner_party")
        election_year = row.get("election_year")
        detail = f"ganador {winner}" if winner else "sin ganador electoral disponible"
        if election_year:
            detail += f" en {election_year}"
        answer_parts.append(f"{section_name}: {detail}.")
        entities.append(
            {
                "type": "section",
                "id": str(row["section_id"]),
                "name": section_name,
                "value": winner,
                "valueLabel": "Partido ganador",
            }
        )

    response_sections = [str(item["response_section_id"]) for item in rows_by_section]
    response = AskResponse(
        answer="Comparación electoral: " + " ".join(answer_parts),
        confidence="high" if len(effective_sections) == len(requested_sections) else "medium",
        resultType="entity_list",
        entities=entities,
        data={
            "tool": "section_profile",
            "operation": "compare_section_profiles",
            "requested_sections": requested_sections,
            "effective_sections": effective_sections,
            "response_sections": response_sections,
            "rows_by_section": rows_by_section,
            "rows": [item["row"] for item in rows_by_section if isinstance(item["row"], dict)],
        },
        sources=sources,
    )
    return SectionComparisonResolution(
        response=response,
        tool_name="section_profile",
        tool_arguments={
            "municipio_id": municipality_id,
            "sections": requested_sections,
            "year": requested_year,
            "include_domains": ["electoral"],
        },
    )
